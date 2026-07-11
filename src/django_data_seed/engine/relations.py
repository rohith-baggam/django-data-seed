"""
Field classification and foreign-key strategy resolution.

This is where the row-explosion bug of 0.4.x is put to bed. The old engine built
a brand-new parent tree for every single child row; v2 defaults to *reusing* an
existing parent row and only creates one when it genuinely has to (an empty
target table, or a OneToOne that needs a fresh, unshared parent).

Foreign keys resolve to a primary-key value -- never a loaded instance -- so the
whole thing stays compatible with ``bulk_create``.
"""

from __future__ import annotations

from enum import Enum

from django.db import models


class FKStrategy(str, Enum):
    """How foreign keys are filled for a run."""

    REUSE = "reuse"    # ? default: point at an existing row
    CREATE = "create"  # ? the old behaviour: always make a fresh parent
    MIX = "mix"        # ? mostly reuse, occasionally create, for realistic spread


def generatable_fields(model: type[models.Model]) -> list[models.Field]:
    """
    The concrete, locally-stored, non-relational fields we generate scalar values
    for -- skipping auto PKs, relations, M2M, reverse accessors, and database-
    computed columns.

    Args:
        - model: The model to inspect.

    Returns:
        - The list of fields the value pipeline should fill.
    """
    fields = []
    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False):
            continue
        if isinstance(field, models.AutoField):
            continue
        if isinstance(field, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
            continue
        if getattr(field, "generated", False):
            # ? Django 5 GeneratedField -- the database computes it, never us.
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            # ? auto_now/auto_now_add are set by Django on save; anything we
            # ? generate would just be overwritten, so leave them alone.
            continue
        fields.append(field)
    return fields


def composite_unique_fields(model: type[models.Model]) -> list[tuple[str, ...]]:
    """
    The multi-column unique constraints on a model, as tuples of field names.

    Covers legacy ``Meta.unique_together`` and plain (non-conditional,
    non-expression) ``UniqueConstraint``s. Single-column constraints are handled
    by the per-field tracker and are excluded here.

    Args:
        - model: The model to inspect.

    Returns:
        - A de-duplicated list of field-name tuples, each with two or more names.
    """
    groups: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()

    for combo in model._meta.unique_together:
        names = tuple(combo)
        if len(names) >= 2 and names not in seen:
            seen.add(names)
            groups.append(names)

    # ? total_unique_constraints = UniqueConstraints with no condition/expressions.
    for constraint in getattr(model._meta, "total_unique_constraints", []):
        names = tuple(constraint.fields)
        if len(names) >= 2 and names not in seen:
            seen.add(names)
            groups.append(names)

    return groups


def relation_fields(model: type[models.Model]) -> list[models.Field]:
    """The concrete local FK / O2O fields on the model."""
    return [
        field
        for field in model._meta.get_fields()
        if isinstance(field, (models.ForeignKey, models.OneToOneField))
        and getattr(field, "concrete", False)
    ]


def m2m_fields(model: type[models.Model]) -> list[models.ManyToManyField]:
    """
    The locally-declared many-to-many fields on the model.

    Uses ``_meta.many_to_many`` rather than filtering ``get_fields()`` on
    ``concrete``: Django 6.0 changed ``ManyToManyField.concrete`` to ``False``,
    which would otherwise make this return nothing (M2M is never attached).
    """
    return list(model._meta.many_to_many)


class RelationResolver:
    """
    Turns a foreign-key field into a concrete parent primary key, honouring the
    chosen strategy and keeping OneToOne parents unique.

    It leans on two things the runner supplies: ``pools`` (a map of model label
    to the primary keys currently available to reuse) and ``ensure_parent`` (a
    callback that creates one fresh parent row and returns its primary key).
    """

    def __init__(self, ctx, pools, ensure_parent, strategy=FKStrategy.REUSE, mix_ratio=0.2):
        self.ctx = ctx
        self.pools = pools
        self.ensure_parent = ensure_parent
        self.strategy = strategy
        self.mix_ratio = mix_ratio

    def resolve(self, model, field, force_null_names):
        """
        Resolves the value for one FK/O2O field.

        Args:
            - model: The model that owns the field.
            - field: The ForeignKey or OneToOneField to fill.
            - force_null_names: Field names on this model that a broken nullable
              cycle edge requires to start out NULL.

        Returns:
            - A parent primary-key value, or ``None`` for a nullable/broken edge.
        """
        target = field.related_model

        if field.name in force_null_names and field.null:
            return None

        # ? OneToOne always needs its own unshared parent, or the unique
        # ? constraint on the relation blows up on the second child.
        if isinstance(field, models.OneToOneField):
            return self.ensure_parent(target)

        if target is model:
            return self._resolve_self_reference(model, field)

        # ? Exercise optional relations: sometimes leave a nullable FK NULL even
        # ? when parents exist, so downstream code that handles "no parent" runs.
        if field.null and self.ctx.rng.random() < self.ctx.null_probability:
            return None

        if self._should_create(field):
            return self.ensure_parent(target)

        pk = self._pick_from_pool(target)
        if pk is not None:
            return pk

        # ? Reuse wanted, but the table is empty: create exactly one parent.
        if field.null:
            return None
        return self.ensure_parent(target)

    # -- internals -----------------------------------------------------------

    def _should_create(self, field) -> bool:
        if self.strategy == FKStrategy.CREATE:
            return True
        if self.strategy == FKStrategy.MIX:
            return self.ctx.rng.random() < self.mix_ratio
        return False

    def _pick_from_pool(self, target):
        pool = self.pools.get(target._meta.label)
        if not pool:
            return None
        # ? Zipf bias: a few "hot" parents collect most of the children, which is
        # ? what real cardinality looks like.
        return pool[self.ctx.zipf_index(len(pool))]

    def _resolve_self_reference(self, model, field):
        """
        Self-referential FK (category trees, org charts). We keep it shallow:
        point at an already-existing row when there is one, otherwise leave it
        NULL so the row becomes a root. A required self-FK with no existing rows
        cannot be satisfied and is left to the caller to surface.
        """
        pk = self._pick_from_pool(model)
        if pk is not None and self.ctx.rng.random() < 0.7:
            return pk
        if field.null:
            return None
        return pk  # ? may be None -> caller reports the impossible required self-FK
