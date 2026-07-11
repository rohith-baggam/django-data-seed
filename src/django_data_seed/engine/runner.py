"""
The runner: turns a list of models into rows.

It ties every other engine module together -- pre-flight, the dependency graph,
the value pipeline, row coherence, the relationship resolver, in-memory
uniqueness (single- and multi-column), and ``bulk_create`` batching -- and drives
an optional reporter so the CLI can show what is happening.

Two promises the plan makes and this module keeps: **one bad model never
vaporises the whole run** (each model is isolated in its own savepoint and its
failure is recorded, not fatal), and **the progress reporter is always shut down
cleanly**, even on a dry run or an exception.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.db import connections, models, transaction

from . import coherence, graph, preflight, providers, relations
from .context import GenContext, resolve_locale
from .generator import UNSET, FieldGenerator
from .preflight import CheckResult
from .relations import FKStrategy, RelationResolver
from .uniqueness import UniquenessTracker


class PreflightFailed(Exception):
    """Raised when a fatal pre-flight check fails and checks were not skipped."""

    def __init__(self, results: list[CheckResult]) -> None:
        self.results = results
        failed = [r for r in results if not r.ok and r.fatal]
        detail = "\n".join(f"  ✖ {r.name}: {r.detail}" for r in failed)
        super().__init__("Pre-flight checks failed:\n" + detail)


class UnsupportedFieldError(Exception):
    """Raised when a *required* field has no generator and can't be left NULL."""

    def __init__(self, report: dict[str, list[str]]) -> None:
        self.report = report
        lines = [
            f"  {label}: {', '.join(names)}" for label, names in report.items()
        ]
        super().__init__(
            "Cannot seed -- these required fields have no generator "
            "(make them nullable, give them a default, register a provider, or "
            "exclude the model):\n" + "\n".join(lines)
        )


@dataclass
class SeedConfig:
    """Everything that shapes a seeding run (mirrors the CLI flags)."""

    count: int = 10
    seed: int | None = None
    locale: object = None
    strategy: FKStrategy = FKStrategy.REUSE
    mix_ratio: float = 0.2
    null_probability: float = 0.1
    realism: str = "smart"
    make_files: bool = True
    batch_size: int = 1000
    atomic: str = "model"  # ? all | model | none
    skip_checks: bool = False
    dry_run: bool = False
    using: str | None = None
    pool_cap: int = 5000  # ? cap reuse pools so huge tables don't bloat memory


@dataclass
class ModelResult:
    """Per-model outcome, used for the closing summary table."""

    label: str
    created: int = 0
    reused_fk: int = 0
    created_fk: int = 0
    elapsed: float = 0.0
    skipped: str | None = None


@dataclass
class SeedResult:
    """The whole run's outcome."""

    per_model: list[ModelResult] = dataclass_field(default_factory=list)
    seed: int | None = None
    elapsed: float = 0.0
    dry_run: bool = False
    plan: dict | None = None  # ? populated on a dry run for --format json

    @property
    def total(self) -> int:
        return sum(r.created for r in self.per_model)

    @property
    def skipped(self) -> list[ModelResult]:
        return [r for r in self.per_model if r.skipped]


class Reporter:
    """No-op reporter. The rich CLI subclasses this to draw the live dashboard."""

    def preflight(self, results: list[CheckResult]) -> None: ...
    def unsupported(self, report: dict[str, list[tuple[str, bool]]]) -> None: ...
    def plan(self, order: graph.SeedOrder, count: int) -> None: ...
    def model_start(self, model, count: int) -> None: ...
    def tick(self, n: int = 1) -> None: ...
    def model_done(self, result: ModelResult) -> None: ...
    def finished(self, result: SeedResult) -> None: ...
    def close(self) -> None: ...


class Runner:
    """Drives one seeding run end to end."""

    def __init__(self, config: SeedConfig, reporter: Reporter | None = None) -> None:
        self.config = config
        self.reporter = reporter or Reporter()
        self.using = config.using or "default"
        self.connection = connections[self.using]

        self.ctx = GenContext(
            locale=resolve_locale(config.locale),
            seed=config.seed,
            use_tz=self._use_tz(),
            null_probability=config.null_probability,
            realism=config.realism,
            make_files=config.make_files,
        )
        self.uniqueness = UniquenessTracker(using=self.using)
        self.field_gen = FieldGenerator(self.ctx, self.uniqueness)
        self.pools: dict[str, list] = {}
        self.resolver = RelationResolver(
            self.ctx,
            self.pools,
            ensure_parent=self._ensure_parent,
            strategy=config.strategy,
            mix_ratio=config.mix_ratio,
        )
        self._current_result: ModelResult | None = None
        self._create_depth = 0
        # ? Primary keys of rows THIS run inserted, per model label. The
        # ? post-insert patch pass may only ever write to these -- never to rows
        # ? that were already in the table (see _wire_self_fk / _wire_forced_null).
        self._created_pks: dict[str, list] = {}

    def _record_created(self, model, created) -> None:
        """
        Records the primary keys of freshly-inserted rows so the patch pass can
        scope itself to this run's data.

        Accepts either model instances (from ``bulk_create``) or bare pks. On the
        rare backend that can't return pks from ``bulk_create`` we fall back to
        the newest rows by pk -- best effort, but it still never reaches back into
        pre-existing data because it is bounded by the number just inserted.
        """
        if not created:
            return
        if isinstance(created[0], models.Model):
            pks = [obj.pk for obj in created if obj.pk is not None]
            if len(pks) != len(created):
                fetched = list(
                    model._base_manager.using(self.using)
                    .order_by("-pk")
                    .values_list("pk", flat=True)[: len(created)]
                )
                pks = list(reversed(fetched))
        else:
            pks = [pk for pk in created if pk is not None]
        self._created_pks.setdefault(model._meta.label, []).extend(pks)

    # -- public entry point --------------------------------------------------

    def run(
        self, model_list: list[type[models.Model]], overrides: dict | None = None
    ) -> SeedResult:
        """
        Seeds every model in ``model_list``.

        Args:
            - model_list: The concrete models to seed.
            - overrides: Optional ``{model_label: {field_name: override}}`` map.

        Returns:
            - A ``SeedResult`` describing what was created.
        """
        overrides = overrides or {}
        seedable = [m for m in model_list if self._is_seedable(m)]

        try:
            return self._run(seedable, overrides)
        finally:
            # ? Whatever happened -- success, dry run, or exception -- never leave
            # ? the live progress display running and the terminal hijacked.
            self.reporter.close()

    def _run(self, seedable, overrides) -> SeedResult:
        results = preflight.run_preflight(self.connection, seedable)
        self.reporter.preflight(results)
        if not self.config.skip_checks and any(not r.ok and r.fatal for r in results):
            raise PreflightFailed(results)

        unsupported = self._analyze_unsupported(seedable)
        self.reporter.unsupported(unsupported)
        required_bad = {
            label: [name for name, required in fields if required]
            for label, fields in unsupported.items()
        }
        required_bad = {label: names for label, names in required_bad.items() if names}
        if required_bad and not self.config.dry_run:
            raise UnsupportedFieldError(required_bad)

        order = graph.build_order(seedable)
        self.reporter.plan(order, self.config.count)

        if self.config.dry_run:
            return SeedResult(
                seed=self.config.seed, dry_run=True, plan=self._serialize_plan(order)
            )

        run_started = time.perf_counter()
        result = SeedResult(seed=self.config.seed)

        if self.config.atomic == "all":
            # ? All-or-nothing: one transaction, no per-model isolation, so the
            # ? first model failure rolls the ENTIRE run back and re-raises.
            with transaction.atomic(using=self.using):
                for model in order.models:
                    result.per_model.append(self._seed_one(model, overrides, order))
                self._patch_pass(order)
        else:
            # ? Isolate each model: a failure is rolled back to its savepoint,
            # ? recorded as skipped, and the rest of the run continues.
            for model in order.models:
                result.per_model.append(self._seed_one(model, overrides, order, isolate=True))
            self._patch_pass(order)

        result.elapsed = time.perf_counter() - run_started
        self.reporter.finished(result)
        return result

    def _seed_one(self, model, overrides, order, isolate: bool = False) -> ModelResult:
        model_overrides = overrides.get(model._meta.label, {})
        force_null = order.force_null_fields.get(model._meta.label, set())
        if isolate:
            return self._seed_model_isolated(model, model_overrides, force_null)
        return self._seed_model(model, model_overrides, force_null)

    # -- per-model seeding ---------------------------------------------------

    def _seed_model_isolated(self, model, overrides, force_null) -> ModelResult:
        """
        Seeds one model, catching any failure so the rest of the run continues.

        The per-model savepoint (unless ``atomic="none"``) rolls back the failed
        model's partial rows; the failure is recorded on the result and shown in
        the summary rather than aborting everything after it.
        """
        try:
            return self._seed_model(model, overrides, force_null)
        except Exception as exc:  # ? isolate the failure to this one model
            self._current_result = None
            outcome = ModelResult(label=model._meta.label, skipped=str(exc))
            self.reporter.model_done(outcome)
            return outcome

    def _seed_model(self, model, overrides, force_null) -> ModelResult:
        outcome = ModelResult(label=model._meta.label)
        self._current_result = outcome
        started = time.perf_counter()
        count = self.config.count

        self.reporter.model_start(model, count)
        self._preload_relation_pools(model)

        scalar_fields = relations.generatable_fields(model)
        rel_fields = relations.relation_fields(model)
        m2m = relations.m2m_fields(model)
        composite = relations.composite_unique_fields(model)
        unique_names = self._unique_field_names(model)
        override_pools = self._prepare_override_pools(overrides, rel_fields)
        create_pools = self._precreate_parents(model, rel_fields, overrides, count)

        per_model_atomic = self.config.atomic != "none"
        ctx = transaction.atomic(using=self.using) if per_model_atomic else _null_context()
        with ctx:
            instances = [
                self._build_instance(
                    model, scalar_fields, rel_fields, overrides, force_null,
                    composite, unique_names, override_pools, create_pools,
                )
                for _ in range(count)
            ]
            created = self._bulk_insert(model, instances, tick=True)
            self._record_created(model, created)
            self._refresh_pool(model)
            if m2m:
                self._attach_m2m(model, created, m2m, overrides)

        outcome.created = count
        outcome.elapsed = time.perf_counter() - started
        self._current_result = None
        self.reporter.model_done(outcome)
        return outcome

    def _build_instance(
        self, model, scalar_fields, rel_fields, overrides, force_null,
        composite, unique_names, override_pools, create_pools,
    ):
        """
        Builds one unsaved instance: scalar values, coherence pass, then FKs.

        When the model has multi-column unique constraints, the whole build is
        retried until the generated value-tuples don't collide in memory.
        """
        skip = set(unique_names) | set(overrides.keys())
        attempts = 120 if composite else 1

        for _ in range(attempts):
            kwargs = {}
            for field in scalar_fields:
                kwargs[field.name] = self.field_gen.value_for(
                    model, field, overrides.get(field.name, UNSET)
                )

            # ? Make the row internally consistent before FKs are attached.
            coherence.apply_coherence(model, kwargs, self.ctx, skip)

            for field in rel_fields:
                kwargs[field.attname] = self._resolve_fk(
                    model, field, overrides, force_null, override_pools, create_pools
                )

            if self._composite_ok(model, composite, kwargs):
                return model(**kwargs)

            # ? This attempt is being thrown away because a composite tuple
            # ? collided -- give back the single-column unique values it reserved
            # ? so a tight value space isn't burned down over the retries.
            self._release_single_uniques(model, scalar_fields, unique_names, overrides, kwargs)

        raise RuntimeError(
            f"Could not satisfy the multi-column unique constraint(s) on "
            f"{model._meta.label} after {attempts} attempts."
        )

    def _release_single_uniques(self, model, scalar_fields, unique_names, overrides, kwargs):
        """Releases the unique scalar values reserved during a discarded attempt."""
        for field in scalar_fields:
            if field.name not in unique_names:
                continue
            if self.uniqueness.is_unbounded(field):
                continue  # ? never reserved by membership, nothing to release
            self.uniqueness.release(model, field, kwargs.get(field.name))

    def _resolve_fk(self, model, field, overrides, force_null, override_pools, create_pools):
        """Resolves one FK/O2O to a pk, honouring overrides, pre-created pools, reuse."""
        if field.name in override_pools:
            pool = override_pools[field.name]
            return self.ctx.rng.choice(pool) if pool else None

        override = overrides.get(field.name, UNSET)
        if override is not UNSET:
            return self._resolve_relation_override(override)

        if field.name in create_pools:
            pk = next(create_pools[field.name], None)
            if pk is not None:
                if self._current_result is not None:
                    self._current_result.created_fk += 1
                return pk

        # ? Track reuse vs. on-demand creation without double-counting.
        created_before = self._current_result.created_fk if self._current_result else 0
        pk = self.resolver.resolve(model, field, force_null)
        if self._current_result is not None and pk is not None:
            if self._current_result.created_fk == created_before:
                self._current_result.reused_fk += 1
        return pk

    def _composite_ok(self, model, composite, kwargs) -> bool:
        """Checks (and, if all clear, reserves) every composite unique tuple."""
        if not composite:
            return True
        pending = []
        for names in composite:
            values = tuple(self._value_for_constraint(model, name, kwargs) for name in names)
            if not self.uniqueness.composite_available(model, names, values):
                return False
            pending.append((names, values))
        for names, values in pending:
            self.uniqueness.add_composite(model, names, values)
        return True

    @staticmethod
    def _value_for_constraint(model, field_name, kwargs):
        """Reads a constraint member's value from kwargs (FKs live under attname)."""
        try:
            field = model._meta.get_field(field_name)
        except Exception:
            return kwargs.get(field_name)
        key = field.attname if field.is_relation else field.name
        return kwargs.get(key)

    # -- bulk insert ---------------------------------------------------------

    def _bulk_insert(self, model, instances, tick: bool):
        """Inserts instances in batches, advancing the progress bar per batch."""
        created = []
        manager = model._base_manager.using(self.using)
        batch_size = self.config.batch_size
        for start in range(0, len(instances), batch_size):
            chunk = instances[start:start + batch_size]
            created.extend(manager.bulk_create(chunk, batch_size=batch_size))
            if tick:
                self.reporter.tick(len(chunk))
        return created

    # -- foreign-key parent creation ----------------------------------------

    def _precreate_parents(self, model, rel_fields, overrides, count) -> dict:
        """
        Under ``--strategy create``, batch-create the ``count`` fresh parents each
        FK needs up front (one bulk_create per target) instead of one INSERT per
        child row. Returns ``{field_name: iterator-of-pks}``.
        """
        if self.config.strategy != FKStrategy.CREATE:
            return {}
        pools: dict = {}
        for field in rel_fields:
            if field.name in overrides:
                continue
            target = field.related_model
            if target is model:
                continue
            pks = self._bulk_create_parents(target, count)
            pools[field.name] = iter(pks)
        return pools

    def _bulk_create_parents(self, target, n) -> list:
        """
        Builds and bulk-inserts ``n`` fresh parent rows of ``target``, returning
        exactly those rows' primary keys -- recovered by *identity* from the
        instances ``bulk_create`` handed back, not by slicing an unordered,
        capped pool (which on PostgreSQL could return arbitrary pre-existing rows).
        """
        scalar_fields = relations.generatable_fields(target)
        rel_fields = relations.relation_fields(target)
        composite = relations.composite_unique_fields(target)
        unique_names = self._unique_field_names(target)
        instances = [
            self._build_instance(
                target, scalar_fields, rel_fields, {}, set(),
                composite, unique_names, {}, {},
            )
            for _ in range(n)
        ]
        created = self._bulk_insert(target, instances, tick=False)
        pks = [obj.pk for obj in created if obj.pk is not None]
        if len(pks) != len(created):
            # ? Backend can't return pks from bulk_create: fall back to the newest
            # ? rows (bounded by n, so still never older pre-existing data).
            fetched = list(
                target._base_manager.using(self.using)
                .order_by("-pk")
                .values_list("pk", flat=True)[: len(created)]
            )
            pks = list(reversed(fetched))
        self._record_created(target, pks)
        self.pools.setdefault(target._meta.label, []).extend(pks)
        return pks

    def _ensure_parent(self, target):
        """
        Creates exactly one fresh parent row of ``target`` and returns its pk.

        Used for OneToOne fields (which need an unshared parent) and for reuse
        against an empty table. Guarded against runaway recursion.
        """
        if self._create_depth > 25:
            raise RuntimeError(
                f"Foreign-key creation nested more than 25 levels deep at "
                f"{target._meta.label}; check for an unintended required-FK chain."
            )
        self._create_depth += 1
        try:
            scalar_fields = relations.generatable_fields(target)
            rel_fields = relations.relation_fields(target)
            composite = relations.composite_unique_fields(target)
            unique_names = self._unique_field_names(target)
            instance = self._build_instance(
                target, scalar_fields, rel_fields, {}, set(),
                composite, unique_names, {}, {},
            )
            saved = target._base_manager.using(self.using).bulk_create([instance])[0]
            if saved.pk is None:
                saved = target._base_manager.using(self.using).order_by("-pk").first()
        finally:
            self._create_depth -= 1

        self.pools.setdefault(target._meta.label, []).append(saved.pk)
        self._record_created(target, [saved.pk])
        if self._current_result is not None:
            self._current_result.created_fk += 1
        return saved.pk

    def _resolve_relation_override(self, override):
        """Turns a non-pooled FK override (instance, pk, callable) into a pk."""
        if callable(override) and not isinstance(override, type):
            override = override()
        if isinstance(override, (list, tuple)):
            override = self.ctx.rng.choice(override)
        if isinstance(override, models.Model):
            return override.pk
        return override  # ? already a pk value

    def _prepare_override_pools(self, overrides, rel_fields) -> dict:
        """
        Resolves QuerySet / list FK overrides to a pk list *once* per model run,
        instead of re-querying for every row (the A5 N+1 fix).
        """
        pools: dict = {}
        for field in rel_fields:
            override = overrides.get(field.name, UNSET)
            if override is UNSET:
                continue
            if hasattr(override, "values_list"):  # ? QuerySet / Manager
                pools[field.name] = list(override.values_list("pk", flat=True))
            elif isinstance(override, (list, tuple)):
                pools[field.name] = [
                    item.pk if isinstance(item, models.Model) else item
                    for item in override
                ]
        return pools

    # -- many-to-many --------------------------------------------------------

    def _attach_m2m(self, model, created, m2m_fields_, overrides):
        """Attaches a small random sample of existing targets to each row."""
        if created and created[0].pk is None:
            created = list(
                model._base_manager.using(self.using).order_by("-pk")[: len(created)]
            )

        for field in m2m_fields_:
            through = field.remote_field.through
            if not through._meta.auto_created:
                continue  # ? explicit through model is seeded as an ordinary model
            target = field.related_model
            self._ensure_pool_loaded(target)
            pool = self.pools.get(target._meta.label) or []
            if not pool:
                continue
            for instance in created:
                sample_size = self.ctx.rng.randint(0, min(5, len(pool)))
                if not sample_size:
                    continue
                chosen = self.ctx.rng.sample(pool, sample_size)
                getattr(instance, field.name).set(chosen)

    # -- post-insert patch pass (self-FK trees + broken cycle edges) ---------

    def _patch_pass(self, order: graph.SeedOrder) -> None:
        """
        Wires relationships that can only be set once rows have primary keys:
        self-referential trees, and the nullable FK edges that were broken to
        untangle a cycle (left NULL at insert time).
        """
        for model in order.models:
            for field in relations.relation_fields(model):
                if field.related_model is model and field.null:
                    self._wire_self_fk(model, field)
            for field_name in order.force_null_fields.get(model._meta.label, set()):
                self._wire_forced_null(model, field_name)

    def _wire_self_fk(self, model, field) -> None:
        """
        Turns this run's self-FK rows into a shallow tree (~20% roots).

        Only rows THIS run inserted are touched -- pre-existing rows (curated
        fixtures, real data on a shared DB) are never rewritten.
        """
        pks = sorted(set(self._created_pks.get(model._meta.label, [])))
        if len(pks) < 2:
            return
        roots = max(1, len(pks) // 5)
        updates = []
        for index in range(roots, len(pks)):
            parent = pks[self.ctx.rng.randrange(0, index)]  # ? an earlier created row
            updates.append(model(pk=pks[index], **{field.attname: parent}))
        if updates:
            model._base_manager.using(self.using).bulk_update(updates, [field.attname])

    def _wire_forced_null(self, model, field_name) -> None:
        """
        Fills a broken-cycle FK (left NULL at insert) from the target pool --
        but only on rows THIS run inserted. A NULL FK on a pre-existing row is a
        legitimate state, not a hole to patch.
        """
        created = self._created_pks.get(model._meta.label, [])
        if not created:
            return
        field = model._meta.get_field(field_name)
        target = field.related_model
        self._ensure_pool_loaded(target)
        pool = self.pools.get(target._meta.label) or []
        if not pool:
            return
        manager = model._base_manager.using(self.using)
        rows = list(
            manager.filter(pk__in=created, **{f"{field.attname}__isnull": True})
            .values_list("pk", flat=True)
        )
        updates = [
            model(pk=pk, **{field.attname: self.ctx.rng.choice(pool)}) for pk in rows
        ]
        if updates:
            manager.bulk_update(updates, [field.attname])

    # -- pools ---------------------------------------------------------------

    def _preload_relation_pools(self, model):
        for field in relations.relation_fields(model):
            if field.related_model is not model:
                self._ensure_pool_loaded(field.related_model)

    def _ensure_pool_loaded(self, target):
        label = target._meta.label
        if label in self.pools:
            return
        self.pools[label] = list(
            target._base_manager.using(self.using)
            .values_list("pk", flat=True)[: self.config.pool_cap]
        )

    def _refresh_pool(self, model):
        self.pools[model._meta.label] = list(
            model._base_manager.using(self.using)
            .values_list("pk", flat=True)[: self.config.pool_cap]
        )

    # -- analysis / helpers --------------------------------------------------

    def _analyze_unsupported(self, model_list) -> dict[str, list[tuple[str, bool]]]:
        """Finds scalar fields with no generator, flagging which are required."""
        report: dict[str, list[tuple[str, bool]]] = {}
        for model in model_list:
            bad = []
            for field in relations.generatable_fields(model):
                if providers.field_is_supported(field):
                    continue
                required = (not field.null) and (not field.has_default())
                bad.append((field.name, required))
            if bad:
                report[model._meta.label] = bad
        return report

    def _serialize_plan(self, order: graph.SeedOrder) -> dict:
        """A JSON-friendly view of the plan, for ``--dry-run --format json``."""
        return {
            "count": self.config.count,
            "order": [m._meta.label for m in order.models],
            "force_null": {
                label: sorted(names) for label, names in order.force_null_fields.items()
            },
        }

    @staticmethod
    def _unique_field_names(model) -> set:
        return {
            f.name
            for f in model._meta.get_fields()
            if getattr(f, "concrete", False) and (f.unique or f.primary_key)
        }

    def _is_seedable(self, model) -> bool:
        meta = model._meta
        return bool(meta.managed and not meta.proxy and not meta.abstract)

    def _use_tz(self) -> bool:
        from django.conf import settings

        return bool(getattr(settings, "USE_TZ", False))


class _null_context:
    """A do-nothing context manager for the ``atomic="none"`` path."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
