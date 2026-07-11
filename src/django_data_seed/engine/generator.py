"""
The value pipeline for a single non-relational field.

Resolution order, first hit wins -- exactly the order the v2 plan lays out:

    1. user override (a value, a callable, a range, or a pool)
    2. NULL injection for nullable, non-unique columns
    3. weighted choice for ``choices`` fields
    4. field-name inference
    5. the field-type provider (MRO dispatch)

then whatever came out is decorated to fit the column (length, numeric range,
decimal shape) and, for unique columns, run through the in-memory uniqueness
tracker. Foreign keys and M2M are *not* handled here -- the relationship engine
owns those.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from . import constraints, inference, providers
from .context import GenContext
from .uniqueness import UniquenessTracker

UNSET = object()

_STRING_FIELDS = (models.CharField, models.TextField)
_INT_FIELDS = (
    models.IntegerField,
    models.SmallIntegerField,
    models.BigIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
    models.PositiveBigIntegerField,
)


class FieldGenerator:
    """
    Produces one value for one concrete field, applying the full resolution
    order and the constraint decoration on top.
    """

    def __init__(self, ctx: GenContext, uniqueness: UniquenessTracker) -> None:
        self.ctx = ctx
        self.uniqueness = uniqueness

    def value_for(self, model: type[models.Model], field: models.Field, override=UNSET):
        """
        Returns a generated (or overridden) value for ``field``.

        Args:
            - model: The model the field belongs to (needed for uniqueness).
            - field: The concrete, non-relational field to fill.
            - override: A user-supplied override, or the ``UNSET`` sentinel.

        Returns:
            - A value ready to hand to ``bulk_create`` / ``objects.create``.
        """
        unique = field.unique or field.primary_key

        if override is not UNSET:
            produce = lambda: self._resolve_override(override)  # noqa: E731
        else:
            if not unique and self._should_null(field):
                return None
            produce = lambda: self._decorate(field, self._raw_value(model, field))  # noqa: E731

        if unique:
            return self._unique_value(model, field, produce)
        return produce()

    def _unique_value(self, model, field, produce, max_tries: int = 200):
        """
        Draws values from ``produce`` until one is unused for this column.

        Plain candidates come first, but once a handful collide we escalate by
        folding seeded entropy into string values -- so a tiny-``max_length``
        unique column (a 13-char ISBN, say) can never dead-end the run. Because
        the entropy comes from ``ctx.rng``, the escalation stays reproducible.
        """
        if self.uniqueness.is_unbounded(field):
            value = produce()
            self.uniqueness.reserve(model, field, value)
            return value

        for attempt in range(max_tries):
            value = produce()
            if attempt >= 8 and isinstance(value, str):
                value = self._inject_entropy(value, field)
            if self.uniqueness.reserve(model, field, value):
                return value

        raise RuntimeError(
            f"Could not generate a unique value for {model._meta.label}.{field.name} "
            f"after {max_tries} tries -- the value space may be too small "
            f"(e.g. a short choices list on a unique field)."
        )

    def _inject_entropy(self, value: str, field: models.Field) -> str:
        """Blends a short seeded token into a string, respecting ``max_length``."""
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        token = "".join(self.ctx.rng.choice(alphabet) for _ in range(5))
        max_length = getattr(field, "max_length", None)
        if max_length:
            head = value[: max(0, max_length - len(token) - 1)]
            return f"{head}-{token}"[:max_length]
        return f"{value}-{token}"

    # -- pipeline steps ------------------------------------------------------

    def _should_null(self, field: models.Field) -> bool:
        """Whether this nullable column should be left NULL for exercise coverage."""
        if not field.null:
            return False
        # ? Don't randomly NULL a column the author gave a default -- that value
        # ? is a deliberate signal about what the column normally holds.
        if field.has_default():
            return False
        return self.ctx.maybe_null()

    def _raw_value(self, model: type[models.Model], field: models.Field):
        """Runs choices -> inference -> type provider and returns the raw value."""
        choices = constraints.choice_values(field)
        if choices:
            return self.ctx.weighted_choice(choices)

        inferred = inference.infer(field, self.ctx)
        if inferred is not inference.UNSET:
            return inferred

        return providers.generate_type_value(field, self.ctx)

    def _resolve_override(self, override):
        """
        Interprets an override: a callable is called, a range/list/tuple is
        sampled, anything else is used verbatim.
        """
        if callable(override) and not isinstance(override, type):
            return override()
        if isinstance(override, range):
            return override[self.ctx.rng.randrange(len(override))]
        if isinstance(override, (list, tuple)):
            return self.ctx.rng.choice(override)
        return override

    def _decorate(self, field: models.Field, value):
        """
        Clamps a raw value to the column: string length, integer range, decimal
        shape. Values from a type provider are already legal, so this is a no-op
        for them -- it matters most for inference outputs (a lat/long float
        landing in a DecimalField, say).
        """
        if value is None:
            return None

        if isinstance(field, _STRING_FIELDS) and isinstance(value, str):
            return constraints.clamp_length(value, field)

        if isinstance(field, models.DecimalField):
            decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
            max_digits, decimal_places = constraints.decimal_params(field)
            return constraints.quantize_decimal(decimal_value, max_digits, decimal_places)

        if isinstance(field, _INT_FIELDS) and not isinstance(field, models.AutoField):
            try:
                integer_value = int(round(float(value)))
            except (TypeError, ValueError):
                return value
            low, high = constraints.integer_bounds(field)
            return max(low, min(high, integer_value))

        if isinstance(field, models.FloatField):
            return float(value)

        return value
