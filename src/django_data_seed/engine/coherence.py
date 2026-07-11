"""
Row coherence: making the fields of a single row agree with each other.

Per-field generation produces values that are individually plausible but
mutually absurd -- a ``created_at`` after ``updated_at``, a first name that has
nothing to do with the email, a US city with a German postcode. This pass runs
*after* all the scalar fields of a row are generated and quietly rewrites the
recognised groups so they tell one consistent story:

  * one **persona** drives ``first_name`` / ``last_name`` / ``full_name`` /
    ``username`` (and the email local-part when the email isn't unique);
  * one **address** drives ``city`` / ``state`` / ``postal_code`` / ``country``;
  * lifecycle **datetimes** are sorted into their natural order
    (``created`` <= ``updated`` <= ``published`` <= ``shipped`` <= ...).

Coherence never touches a field the user overrode or a unique field (rewriting
those would bypass the override or the uniqueness guarantee), so it is always
safe to run.
"""

from __future__ import annotations

import datetime

# ? Lifecycle ordering: earlier stages first. A field whose name contains one of
# ? these ranks by its index; unranked date fields keep their place.
_LIFECYCLE_ORDER = [
    "created",
    "registered",
    "signed_up",
    "started",
    "updated",
    "modified",
    "confirmed",
    "approved",
    "published",
    "paid",
    "shipped",
    "delivered",
    "completed",
    "closed",
    "cancelled",
    "deleted",
    "expired",
]

_PERSONA_FIRST = ("first_name", "firstname", "given_name", "fname")
_PERSONA_LAST = ("last_name", "lastname", "surname", "family_name", "lname")
_PERSONA_FULL = ("full_name", "fullname", "display_name")
_PERSONA_USER = ("username", "user_name", "login", "handle")

_ADDR_CITY = ("city", "town")
_ADDR_STATE = ("state", "province", "region")
_ADDR_ZIP = ("postal_code", "postcode", "zip_code", "zip", "pincode")
_ADDR_COUNTRY = ("country", "nation")


def apply_coherence(model, field_values: dict, ctx, skip: set) -> None:
    """
    Rewrites recognised field groups in ``field_values`` so the row is internally
    consistent. Mutates ``field_values`` in place.

    Args:
        - model: The model being seeded (used for field lookups).
        - field_values: The generated ``{field_name: value}`` for one row.
        - ctx: The active generation context.
        - skip: Field names that must not be rewritten (user overrides + unique).
    """
    if not ctx.smart():
        return
    _apply_persona(model, field_values, ctx, skip)
    _apply_address(field_values, ctx, skip)
    _order_lifecycle_dates(model, field_values, skip)


def _name_index(field_name: str, group: tuple[str, ...]) -> bool:
    lowered = field_name.lower()
    return any(token in lowered for token in group)


def _writable(field_values: dict, name: str, skip: set) -> bool:
    return name in field_values and name not in skip


def _apply_persona(model, field_values, ctx, skip) -> None:
    """Drives all name-ish fields from one generated person."""
    firsts = [f for f in field_values if _name_index(f, _PERSONA_FIRST)]
    lasts = [f for f in field_values if _name_index(f, _PERSONA_LAST)]
    fulls = [f for f in field_values if _name_index(f, _PERSONA_FULL)]
    users = [f for f in field_values if _name_index(f, _PERSONA_USER)]

    if not (firsts or lasts or fulls or users):
        return
    # ? Only bother when there's more than one name-ish field to keep in sync.
    if len(firsts) + len(lasts) + len(fulls) + len(users) < 2:
        return

    first = ctx.person.first_name()
    last = ctx.person.last_name()
    for name in firsts:
        if _writable(field_values, name, skip):
            field_values[name] = _fit(model, name, first)
    for name in lasts:
        if _writable(field_values, name, skip):
            field_values[name] = _fit(model, name, last)
    for name in fulls:
        if _writable(field_values, name, skip):
            field_values[name] = _fit(model, name, f"{first} {last}")
    for name in users:
        if _writable(field_values, name, skip):
            handle = f"{first}.{last}{ctx.rng.randint(1, 999)}".lower()
            field_values[name] = _fit(model, name, handle)


def _apply_address(field_values, ctx, skip) -> None:
    """Drives city/state/zip/country from one generated address record."""
    city = [f for f in field_values if _name_index(f, _ADDR_CITY)]
    state = [f for f in field_values if _name_index(f, _ADDR_STATE)]
    zips = [f for f in field_values if _name_index(f, _ADDR_ZIP)]
    country = [f for f in field_values if _name_index(f, _ADDR_COUNTRY)]

    if len(city) + len(state) + len(zips) + len(country) < 2:
        return

    for name in city:
        if _writable(field_values, name, skip):
            field_values[name] = ctx.address.city()
    for name in state:
        if _writable(field_values, name, skip):
            field_values[name] = ctx.address.state()
    for name in zips:
        if _writable(field_values, name, skip):
            field_values[name] = ctx.address.postal_code()
    for name in country:
        if _writable(field_values, name, skip):
            field_values[name] = ctx.address.country()


def _order_lifecycle_dates(model, field_values, skip) -> None:
    """Sorts recognised lifecycle date/datetime fields into their natural order."""
    # ? date and datetime can't be compared to each other, so bucket them apart
    # ? -- a DateField column and a DateTimeField column are ordered separately.
    datetimes = []
    dates = []
    for name, value in field_values.items():
        if name in skip:
            continue
        rank = _lifecycle_rank(name)
        if rank is None:
            continue
        if isinstance(value, datetime.datetime):
            datetimes.append((rank, name, value))
        elif isinstance(value, datetime.date):
            dates.append((rank, name, value))

    for bucket in (datetimes, dates):
        if len(bucket) < 2:
            continue
        # ? Keep the generated values but reassign them ascending to the fields
        # ? ranked earliest-first, so created <= updated <= shipped <= ...
        ordered_fields = [name for _rank, name, _value in sorted(bucket, key=lambda t: t[0])]
        ordered_values = sorted(value for _rank, _name, value in bucket)
        for name, value in zip(ordered_fields, ordered_values, strict=True):
            field_values[name] = value


def _lifecycle_rank(field_name: str):
    lowered = field_name.lower()
    for index, token in enumerate(_LIFECYCLE_ORDER):
        if token in lowered:
            return index
    return None


def _fit(model, field_name: str, value: str) -> str:
    """Clamps a coherence value to the field's ``max_length`` if it has one."""
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        return value
    max_length = getattr(field, "max_length", None)
    if max_length is not None and len(value) > max_length:
        return value[:max_length]
    return value
