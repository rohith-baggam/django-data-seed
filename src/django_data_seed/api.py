"""
The public Python API.

The management command is a thin wrapper over ``seed()``; everything the command
can do is available in code too, so seeding fits into scripts, fixtures, and
tests without shelling out. This is the surface the v2 plan calls "a real API,
not just a command".
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.db import models

from .discovery import select_models
from .engine.relations import FKStrategy
from .engine.runner import Reporter, Runner, SeedConfig, SeedResult


def _normalize_target(target, exclude) -> list[type[models.Model]]:
    """Turns the many accepted ``target`` shapes into a list of model classes."""
    if target is None:
        return select_models(None, exclude)
    if isinstance(target, (list, tuple, set)):
        resolved: list[type[models.Model]] = []
        for item in target:
            resolved.extend(_normalize_target(item, exclude))
        # ? De-dup while preserving order.
        seen: set[str] = set()
        unique = []
        for model in resolved:
            if model._meta.label not in seen:
                seen.add(model._meta.label)
                unique.append(model)
        return unique
    if isinstance(target, str):
        # ? select_models() handles both "app_label" and "app_label.Model".
        return select_models([target], exclude)
    if isinstance(target, type) and issubclass(target, models.Model):
        return [target]
    raise TypeError(f"Unsupported seed target: {target!r}")


def _normalize_overrides(overrides, model_list) -> dict:
    """
    Accepts either ``{field: override}`` (for a single target model) or
    ``{model_label: {field: override}}`` (for several), and returns the latter.
    """
    if not overrides:
        return {}
    looks_per_model = all(
        isinstance(value, dict) and "." in str(key) for key, value in overrides.items()
    )
    if looks_per_model:
        return overrides
    if len(model_list) == 1:
        return {model_list[0]._meta.label: overrides}
    raise ValueError(
        "Ambiguous overrides: with more than one target model, pass overrides as "
        "{'app_label.Model': {'field': ...}}."
    )


def seed(
    target=None,
    count: int = 10,
    *,
    overrides: dict | None = None,
    seed: int | None = None,
    locale=None,
    strategy: str = "reuse",
    mix_ratio: float = 0.2,
    exclude=None,
    using: str | None = None,
    realism: str = "smart",
    null_probability: float = 0.1,
    atomic: str = "model",
    skip_checks: bool = False,
    dry_run: bool = False,
    make_files: bool = True,
    batch_size: int = 1000,
    reporter: Reporter | None = None,
) -> SeedResult:
    """
    Seeds one model, several models, or the whole project.

    Args:
        - target: A model class, an ``"app_label.Model"`` / ``"app_label"``
          string, a list of those, or ``None`` for every project model.
        - count: Rows to create per model.
        - overrides: Per-field overrides (see ``_normalize_overrides``).
        - seed: RNG seed for a byte-for-byte reproducible run.
        - locale: Locale code/enum driving realistic text (e.g. ``"de"``).
        - strategy: Foreign-key strategy -- ``"reuse"``, ``"create"`` or ``"mix"``.
        - mix_ratio: For ``strategy="mix"``, the chance of creating a fresh parent.
        - exclude: Glob patterns of labels/apps to skip (whole-project mode).
        - using: Database alias to seed into.
        - realism: ``"smart"`` (distributions/temporal shapes) or ``"uniform"``.
        - null_probability: Chance a nullable, non-required column is left NULL.
        - atomic: Transaction scope -- ``"all"``, ``"model"`` or ``"none"``.
        - skip_checks: Bypass the pre-flight phase.
        - batch_size: ``bulk_create`` batch size.
        - reporter: Optional reporter for progress output.

    Returns:
        - A ``SeedResult`` summarising what was created.
    """
    model_list = _normalize_target(target, exclude)
    if not model_list:
        raise ValueError("No models matched the given target/exclude selection.")

    config = SeedConfig(
        count=count,
        seed=seed,
        locale=locale,
        strategy=FKStrategy(strategy),
        mix_ratio=mix_ratio,
        null_probability=null_probability,
        realism=realism,
        batch_size=batch_size,
        atomic=atomic,
        skip_checks=skip_checks,
        dry_run=dry_run,
        make_files=make_files,
        using=using,
    )
    runner = Runner(config, reporter)
    return runner.run(model_list, _normalize_overrides(overrides, model_list))


@dataclass
class SeedPlan:
    """
    A small declarative, reusable seed plan -- the programmatic form of a
    ``seed.yaml``. Each entry names a target and its per-target settings.

    Example:
        >>> plan = SeedPlan()
        >>> plan.add("shop.Author", count=20)
        >>> plan.add("shop.Book", count=100, strategy="reuse")
        >>> plan.run(seed=42)
    """

    entries: list[dict] = dataclass_field(default_factory=list)
    defaults: dict = dataclass_field(default_factory=dict)

    def add(self, target, **options) -> SeedPlan:
        """Adds a target with its options; returns ``self`` for chaining."""
        entry = {"target": target}
        entry.update(options)
        self.entries.append(entry)
        return self

    def run(self, **run_defaults) -> list[SeedResult]:
        """
        Executes every entry in declaration order.

        Args:
            - run_defaults: Options applied to all entries unless overridden
              (e.g. ``seed=42``, ``using="default"``).

        Returns:
            - The per-entry ``SeedResult`` objects.
        """
        results = []
        for entry in self.entries:
            options = {**self.defaults, **run_defaults, **entry}
            target = options.pop("target")
            results.append(seed(target, **options))
        return results

    @classmethod
    def from_dict(cls, data: dict) -> SeedPlan:
        """
        Builds a plan from a parsed mapping like::

            {"defaults": {"seed": 42},
             "models": {"shop.Author": {"count": 20},
                        "shop.Book": {"count": 100}}}
        """
        plan = cls(defaults=data.get("defaults", {}))
        for target, options in data.get("models", {}).items():
            plan.add(target, **(options or {}))
        return plan
