"""
In-memory uniqueness tracking.

The 0.4.x engine hit the database with a ``filter(...).exists()`` for every
unique value it generated -- an N+1 storm, and it even did it for UUID4 columns
whose collision odds are cosmological. Here we load each unique column's
existing values into a set exactly once, then generate against that set in
memory with zero further round-trips.

Two shapes of uniqueness are tracked: single-column ``unique=True`` and
multi-column ``unique_together`` / ``UniqueConstraint(fields=...)`` (plain,
non-conditional constraints only -- conditional/expression constraints are
best-effort and left to the database).
"""

from __future__ import annotations

import uuid

from django.db import models

# ? Field types whose value space is so large that a collision check is pointless.
_UNBOUNDED = (models.UUIDField,)


class UniquenessTracker:
    """
    Remembers which values have already been used for each unique column, both
    the rows already in the database and the ones we generate during a run.

    ``using`` names the database alias every preload query runs against, so a
    multi-database run checks the *target* connection, not ``default``.
    """

    def __init__(self, using: str = "default") -> None:
        self.using = using
        self._used: dict[tuple[str, str], set] = {}
        self._loaded: set[tuple[str, str]] = set()
        # ? Composite keys: (model_label, field-name tuple) -> set of value tuples.
        self._composite: dict[tuple[str, tuple[str, ...]], set] = {}
        self._composite_loaded: set[tuple[str, tuple[str, ...]]] = set()

    @staticmethod
    def _key(model: type[models.Model], field: models.Field) -> tuple[str, str]:
        return (model._meta.label, field.name)

    @staticmethod
    def is_unbounded(field: models.Field) -> bool:
        """Whether the field's value space is too large to bother checking."""
        return isinstance(field, _UNBOUNDED)

    def preload(self, model: type[models.Model], field: models.Field) -> None:
        """
        Loads the column's current distinct values into memory, once.

        Args:
            - model: The model owning the column.
            - field: The unique field whose values are pulled.
        """
        key = self._key(model, field)
        if key in self._loaded:
            return
        self._loaded.add(key)

        bucket = self._used.setdefault(key, set())
        if self.is_unbounded(field):
            # ? Nothing to preload; we never check membership for these.
            return
        manager = model._base_manager.using(self.using)
        for value in manager.values_list(field.name, flat=True).iterator():
            if value is not None:
                bucket.add(_hashable(value))

    def reserve(self, model, field, value) -> bool:
        """
        Claims ``value`` for a unique column if it is still free.

        Args:
            - model: The model owning the column.
            - field: The unique field.
            - value: A candidate value.

        Returns:
            - ``True`` if the value was unused and is now reserved, ``False`` if
              it collides with an existing/already-reserved value.
        """
        key = self._key(model, field)
        self.preload(model, field)
        bucket = self._used.setdefault(key, set())

        if self.is_unbounded(field):
            # ? Value space is astronomical; never collides in practice.
            bucket.add(_hashable(value))
            return True

        marker = _hashable(value)
        if marker in bucket:
            return False
        bucket.add(marker)
        return True

    def remember(self, model, field, value) -> None:
        """Records an externally chosen value so later rows avoid it."""
        self.preload(model, field)
        self._used.setdefault(self._key(model, field), set()).add(_hashable(value))

    def release(self, model, field, value) -> None:
        """
        Returns a previously-reserved single-column value to the free pool.

        Used when a row build is discarded (a multi-column constraint collided)
        so the single-column values it reserved along the way aren't burned --
        which would otherwise shrink a tight unique space with every retry.
        """
        if value is None:
            return
        bucket = self._used.get(self._key(model, field))
        if bucket is not None:
            bucket.discard(_hashable(value))

    # -- composite (multi-column) uniqueness --------------------------------

    def preload_composite(self, model, field_names: tuple[str, ...]) -> None:
        """Loads existing value-tuples for a multi-column unique constraint, once."""
        key = (model._meta.label, field_names)
        if key in self._composite_loaded:
            return
        self._composite_loaded.add(key)

        bucket = self._composite.setdefault(key, set())
        manager = model._base_manager.using(self.using)
        for row in manager.values_list(*field_names).iterator():
            bucket.add(tuple(_hashable(v) for v in row))

    def composite_available(self, model, field_names: tuple[str, ...], values: tuple) -> bool:
        """Read-only check: would this value-tuple be free (no reservation made)?"""
        if any(v is None for v in values):
            return True  # ? NULLs never collide in SQL.
        self.preload_composite(model, field_names)
        bucket = self._composite.setdefault((model._meta.label, field_names), set())
        return tuple(_hashable(v) for v in values) not in bucket

    def add_composite(self, model, field_names: tuple[str, ...], values: tuple) -> None:
        """Records a value-tuple as used (skips tuples containing a NULL)."""
        if any(v is None for v in values):
            return
        self.preload_composite(model, field_names)
        bucket = self._composite.setdefault((model._meta.label, field_names), set())
        bucket.add(tuple(_hashable(v) for v in values))

    def reserve_composite(self, model, field_names: tuple[str, ...], values: tuple) -> bool:
        """
        Claims a value-tuple for a multi-column constraint if still free.

        Args:
            - model: The model owning the constraint.
            - field_names: The constrained field names, in order.
            - values: The candidate values, aligned to ``field_names``.

        Returns:
            - ``True`` if the tuple was free (now reserved), ``False`` on collision.
        """
        key = (model._meta.label, field_names)
        self.preload_composite(model, field_names)
        bucket = self._composite.setdefault(key, set())

        marker = tuple(_hashable(v) for v in values)
        # ? A NULL in any column means the row can't collide (SQL NULLs are
        # ? distinct), so it is always accepted.
        if any(v is None for v in values):
            return True
        if marker in bucket:
            return False
        bucket.add(marker)
        return True


def _hashable(value):
    """Coerces unhashable-but-comparable values (like UUID) into a stable key."""
    if isinstance(value, uuid.UUID):
        return str(value)
    return value
