"""
Constraint helpers: the layer that clamps whatever a provider dreamed up so it
actually fits the column.

The 0.4.x engine leaked bugs here -- decimals that ignored ``max_digits``, char
values sliced by ``max_length - 1`` for no reason, integer ranges never read at
all. Everything to do with "make this value legal for this field" lives in one
place now so a provider can stay dumb and a field can stay strict.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# * Conservative, backend-independent ranges for Django's integer field types.
# ? We deliberately avoid touching a DB connection so bounds work at plan time.
INTEGER_RANGES: dict[str, tuple[int, int]] = {
    "SmallIntegerField": (-32768, 32767),
    "IntegerField": (-2147483648, 2147483647),
    "BigIntegerField": (-9223372036854775808, 9223372036854775807),
    "PositiveSmallIntegerField": (0, 32767),
    "PositiveIntegerField": (0, 2147483647),
    "PositiveBigIntegerField": (0, 9223372036854775807),
}

# ? A friendly window we generate inside unless the field's own validators
# ? demand something wider -- keeps seeded numbers human-sized and believable.
FRIENDLY_MAGNITUDE = 10_000


def validator_bounds(field: models.Field) -> tuple[int | float | None, int | float | None]:
    """
    Pulls explicit ``MinValueValidator`` / ``MaxValueValidator`` limits off a
    field, if the model author declared any.

    Args:
        - field: Any Django model field.

    Returns:
        - A ``(min, max)`` tuple where either element may be ``None`` when the
          corresponding validator is absent.
    """
    low: int | float | None = None
    high: int | float | None = None
    for validator in getattr(field, "validators", []):
        if isinstance(validator, MinValueValidator):
            low = validator.limit_value
        elif isinstance(validator, MaxValueValidator):
            high = validator.limit_value
    return low, high


def integer_bounds(field: models.Field) -> tuple[int, int]:
    """
    Resolves the legal ``(low, high)`` range for an integer field, honouring
    both the field type's storage range and any explicit validators.

    Args:
        - field: An integer-flavoured Django field.

    Returns:
        - A ``(low, high)`` tuple that is always safe to generate within.
    """
    hard_low, hard_high = INTEGER_RANGES.get(field.get_internal_type(), (-(2**31), 2**31 - 1))

    v_low, v_high = validator_bounds(field)
    low = hard_low if v_low is None else max(hard_low, int(v_low))
    high = hard_high if v_high is None else min(hard_high, int(v_high))

    # ? When the author left the range wide open, shrink to a friendly window so
    # ? we don't scatter values across billions. Explicit validators win outright.
    if v_low is None:
        low = max(low, 0 if hard_low >= 0 else -FRIENDLY_MAGNITUDE)
    if v_high is None:
        high = min(high, FRIENDLY_MAGNITUDE)

    if low > high:
        # ? Pathological validator combination -- fall back to the hard range.
        low, high = hard_low, hard_high
    return low, high


def decimal_params(field: models.DecimalField) -> tuple[int, int]:
    """
    Returns a sane ``(max_digits, decimal_places)`` pair for a DecimalField,
    filling in defaults when the author left them unset.

    Args:
        - field: A Django ``DecimalField``.

    Returns:
        - A ``(max_digits, decimal_places)`` tuple with ``max_digits`` always
          greater than ``decimal_places``.
    """
    decimal_places = field.decimal_places if field.decimal_places is not None else 2
    max_digits = field.max_digits if field.max_digits is not None else decimal_places + 6
    # ? Guard against author typos where places would swallow the whole number.
    if max_digits <= decimal_places:
        max_digits = decimal_places + 1
    return max_digits, decimal_places


def quantize_decimal(value: Decimal, max_digits: int, decimal_places: int) -> Decimal:
    """
    Clamps a decimal so it never exceeds ``max_digits`` total or overflows its
    ``decimal_places``.

    Args:
        - value: The raw decimal to shape.
        - max_digits: Total number of significant digits the column allows.
        - decimal_places: Digits allowed after the point.

    Returns:
        - A ``Decimal`` that fits the column exactly.
    """
    whole_digits = max_digits - decimal_places
    ceiling = Decimal(10) ** whole_digits
    quant = Decimal(1).scaleb(-decimal_places)  # e.g. 0.01 for two places
    shaped = value.copy_abs() % ceiling
    shaped = shaped.quantize(quant, rounding=ROUND_DOWN)
    if value < 0:
        shaped = -shaped
    return shaped


def clamp_length(value: str, field: models.Field) -> str:
    """
    Truncates a string to the field's ``max_length`` -- properly, at the exact
    boundary rather than the ``max_length - 1`` the old engine used.

    Args:
        - value: The candidate string.
        - field: The field whose ``max_length`` bounds it (may be ``None``).

    Returns:
        - ``value`` unchanged, or sliced to ``max_length`` characters.
    """
    max_length = getattr(field, "max_length", None)
    if max_length is not None and len(value) > max_length:
        return value[:max_length]
    return value


def choice_values(field: models.Field) -> Sequence | None:
    """
    Flattens a field's ``choices`` (including grouped choices) into a plain list
    of stored values, or ``None`` when the field has no choices.

    Args:
        - field: Any Django model field.

    Returns:
        - A list of choosable stored values, or ``None``.
    """
    choices = getattr(field, "choices", None)
    if not choices:
        return None

    values = []
    for stored, label in choices:
        if isinstance(label, (list, tuple)):
            # ? Grouped choices: the second element is itself a list of pairs.
            values.extend(inner_stored for inner_stored, _ in label)
        else:
            values.append(stored)
    return values
