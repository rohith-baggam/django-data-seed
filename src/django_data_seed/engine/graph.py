"""
The foreign-key dependency graph and topological ordering.

0.4.x seeded models in whatever order ``apps.get_models()`` returned and created
a fresh parent tree per child, which both exploded row counts and blew the stack
on cyclic relations. v2 builds the FK graph up front, seeds parents before
children, and breaks cycles deliberately at nullable foreign keys instead of
recursing forever. A cycle made entirely of *non*-nullable keys is reported as a
clear error -- with the offending path printed -- rather than a crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.db import models


class HardCycleError(Exception):
    """
    Raised when the selected models contain a cycle of non-nullable foreign keys
    that cannot be seeded in any order.
    """

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(
            "Cannot seed: the models form a required (non-nullable) foreign-key "
            f"cycle that has no valid insert order:\n    {path}\n"
            "Make one of the foreign keys in this cycle nullable, or exclude one "
            "of the models, so the cycle can be broken."
        )


@dataclass
class SeedOrder:
    """
    The result of ordering the selected models for seeding.

    Attributes:
        - models: The models in a safe insert order (parents before children).
        - force_null_fields: Per model, the FK field names that had to be left
          NULL initially because a nullable cycle edge was broken. These rows are
          valid as-is; a later patch pass may fill them.
    """

    models: list[type[models.Model]]
    force_null_fields: dict[str, set[str]] = dataclass_field(default_factory=dict)


def _dependency_fields(model: type[models.Model], selected: set) -> list[models.Field]:
    """
    Returns the concrete FK/O2O fields on ``model`` that point at another model
    in the selected set (self-references are not ordering edges).
    """
    edges = []
    for field in model._meta.get_fields():
        if not isinstance(field, (models.ForeignKey, models.OneToOneField)):
            continue
        if getattr(field, "auto_created", False) and not field.concrete:
            # ? Reverse accessor, not a real column.
            continue
        target = field.related_model
        if target is model or target not in selected:
            continue
        edges.append(field)
    return edges


def _m2m_targets(model: type[models.Model], selected: set) -> list[type[models.Model]]:
    """
    The selected models this model links to via a locally-declared M2M field.

    Uses ``_meta.many_to_many`` (stable across Django versions) rather than the
    ``concrete`` flag, which Django 6.0 flipped to ``False`` for M2M fields.
    """
    targets = []
    for field in model._meta.many_to_many:
        target = field.related_model
        if target is not model and target in selected:
            targets.append(target)
    return targets


def build_order(model_list: list[type[models.Model]]) -> SeedOrder:
    """
    Topologically orders the models so every parent is seeded before its
    children, breaking nullable cycles and rejecting non-nullable ones.

    Args:
        - model_list: The models selected for seeding.

    Returns:
        - A ``SeedOrder`` with the insert order and any broken (force-NULL) edges.

    Raises:
        - HardCycleError: When a non-nullable FK cycle makes ordering impossible.
    """
    selected = set(model_list)

    # ? deps[model] = models that must be seeded first. Soft (nullable) edges can
    # ? be dropped to break a cycle; hard edges cannot.
    hard: dict = {m: set() for m in model_list}
    soft: dict = {m: set() for m in model_list}
    soft_fields: dict = {m: {} for m in model_list}

    for model in model_list:
        for dep_field in _dependency_fields(model, selected):
            target = dep_field.related_model
            if dep_field.null:
                soft[model].add(target)
                soft_fields[model].setdefault(target, set()).add(dep_field.name)
            else:
                hard[model].add(target)
        # ? M2M targets should exist before we try to attach them, but the link
        # ? is always optional, so it is a soft (breakable) ordering edge with no
        # ? column to force NULL.
        for m2m_target in _m2m_targets(model, selected):
            soft[model].add(m2m_target)

    deps = {m: set(hard[m]) | set(soft[m]) for m in model_list}
    force_null: dict[str, set[str]] = {}

    order: list = []
    resolved: set = set()
    remaining = list(model_list)

    while remaining:
        ready = [m for m in remaining if deps[m] <= resolved]
        if not ready:
            # ? A cycle among the remaining models. Break one soft edge and retry.
            if not _break_one_soft_edge(remaining, deps, soft, soft_fields, force_null):
                raise HardCycleError(_find_hard_cycle(remaining, hard))
            continue
        # ? Deterministic tie-breaking keeps runs reproducible.
        for model in sorted(ready, key=lambda m: m._meta.label):
            order.append(model)
            resolved.add(model)
            remaining.remove(model)

    return SeedOrder(models=order, force_null_fields=force_null)


def _break_one_soft_edge(remaining, deps, soft, soft_fields, force_null) -> bool:
    """
    Drops a single nullable dependency edge that sits inside the current cycle,
    recording the field(s) that must therefore start out NULL.

    Returns:
        - ``True`` if an edge was broken, ``False`` if no soft edge remains.
    """
    remaining_set = set(remaining)
    for model in sorted(remaining, key=lambda m: m._meta.label):
        breakable = soft[model] & remaining_set & deps[model]
        if not breakable:
            continue
        target = sorted(breakable, key=lambda m: m._meta.label)[0]
        deps[model].discard(target)
        broken = soft_fields[model].get(target, set())
        if broken:
            force_null.setdefault(model._meta.label, set()).update(broken)
        return True
    return False


def _find_hard_cycle(remaining, hard) -> list[str]:
    """
    Walks the non-nullable edges among the stuck models to recover one concrete
    cycle path for the error message.
    """
    remaining_set = set(remaining)
    start = sorted(remaining, key=lambda m: m._meta.label)[0]
    path: list = []
    seen: set = set()
    node = start
    while node not in seen:
        seen.add(node)
        path.append(node._meta.label)
        nxt = sorted(hard[node] & remaining_set, key=lambda m: m._meta.label)
        if not nxt:
            break
        node = nxt[0]
    path.append(node._meta.label)
    return path
