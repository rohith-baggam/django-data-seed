"""
Field-name inference.

A ``CharField`` called ``city`` should hold ``"Rotterdam"``, not ``"Lorem ipsum
dolor"``. This module reads the *name* of a field and, when it recognises a
common semantic (email, city, price, latitude, ...), hands back a value from the
matching Mimesis provider. It is the single feature that makes a seeded demo
screenshot look like a real product.

Inference sits between the user override and the raw type provider in the
resolution order, so a type is still always respected -- a numeric field only
ever draws from numeric rules, a text field only from text rules.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from django.db import models

from .context import GenContext

# ? Sentinel: distinguishes "no name rule matched" from a legitimately generated
# ? ``None``/empty value.
UNSET = object()

# ? Fields that already carry their own strong semantics via a dedicated provider
# ? -- we don't let name inference second-guess them (a URLField should stay a URL).
_SPECIALISED = (
    models.EmailField,
    models.SlugField,
    models.URLField,
    models.GenericIPAddressField,
    models.UUIDField,
)

Rule = tuple[tuple[str, ...], Callable[[GenContext], object]]


def _matches(name: str, tokens: Iterable[str]) -> bool:
    """
    Whether a field name expresses one of ``tokens``.

    Matching is segment-aware: ``user_name`` matches ``name`` only because we
    also test whole underscore/camel segments, while short tokens must appear as
    a full segment to avoid ``filename`` masquerading as a person's name.

    Args:
        - name: The lower-cased field name.
        - tokens: Candidate semantic tokens to test against the name.

    Returns:
        - ``True`` when any token describes the field.
    """
    segments = set(re.split(r"[^a-z0-9]+", name))
    for token in tokens:
        normalised = token.replace(" ", "_")
        if "_" in normalised:
            if normalised in name:
                return True
        elif token in segments:
            return True
        elif len(token) >= 6 and token in name:
            return True
    return False


def _is_string_field(field: models.Field) -> bool:
    return isinstance(field, (models.CharField, models.TextField))


def _is_number_field(field: models.Field) -> bool:
    return isinstance(
        field, (models.IntegerField, models.FloatField, models.DecimalField)
    ) and not isinstance(field, models.AutoField)


# ---------------------------------------------------------------------------
# * Text rules, ordered from most specific to most general. The first match
# * wins, so ``username`` resolves before the catch-all ``name`` rule.
# ---------------------------------------------------------------------------

_TEXT_RULES: list[Rule] = [
    (("email", "email_address", "e_mail"), lambda c: c.person.email()),
    (("username", "user_name", "login", "handle"), lambda c: c.person.username()),
    (("first_name", "firstname", "given_name", "fname"), lambda c: c.person.first_name()),
    (("last_name", "lastname", "surname", "family_name", "lname"), lambda c: c.person.last_name()),
    (("company_name", "company", "organisation", "organization", "employer"),
     lambda c: c.finance.company()),
    (("full_name", "fullname", "display_name"), lambda c: c.person.full_name()),
    (("job", "occupation", "designation", "profession", "job_title"),
     lambda c: c.person.occupation()),
    (("city", "town"), lambda c: c.address.city()),
    (("country_code",), lambda c: c.address.country_code()),
    (("country", "nation"), lambda c: c.address.country()),
    (("state", "province", "region"), lambda c: c.address.state()),
    (("street", "address_line", "street_name"), lambda c: c.address.street_name()),
    (("address",), lambda c: c.address.address()),
    (("postal_code", "postcode", "zip_code", "zip", "pincode"),
     lambda c: c.address.postal_code()),
    (("phone", "mobile", "telephone", "contact_number", "phone_number"),
     lambda c: c.person.phone_number()),
    (("currency",), lambda c: c.finance.currency_iso_code()),
    (("color", "colour"), lambda c: c.text.color()),
    (("mac_address", "mac"), lambda c: c.internet.mac_address()),
    (("title", "headline", "subject", "heading"), lambda c: c.text.title()),
    (("description", "summary", "bio", "about", "content", "body", "notes",
      "comment", "message", "remarks"), lambda c: c.text.text(quantity=2)),
    (("name", "label"), lambda c: c.person.full_name()),
]

# ---------------------------------------------------------------------------
# * Numeric rules. Producers return plain numbers; the generator coerces them to
# * the field's exact type (int / float / Decimal) afterwards.
# ---------------------------------------------------------------------------

_NUMBER_RULES: list[Rule] = [
    (("latitude", "lat"), lambda c: float(c.address.latitude())),
    (("longitude", "lng", "lon", "long"), lambda c: float(c.address.longitude())),
    (("price", "amount", "cost", "total", "salary", "balance", "fee", "revenue",
      "subtotal", "payment"), lambda c: c.lognormal(mean=120.0)),
    (("age",), lambda c: c.rng.randint(18, 90)),
    (("year",), lambda c: c.rng.randint(1990, 2025)),
    (("quantity", "qty", "count", "stock", "units"), lambda c: c.rng.randint(0, 500)),
    (("rating", "stars"), lambda c: c.rng.randint(1, 5)),
    (("score", "points"), lambda c: c.rng.randint(0, 100)),
    (("percent", "percentage", "discount"), lambda c: round(c.rng.uniform(0, 100), 2)),
]


def infer(field: models.Field, ctx: GenContext):
    """
    Returns a name-inferred value for a field, or ``UNSET`` when no rule matches.

    Args:
        - field: The model field being generated.
        - ctx: The active generation context.

    Returns:
        - A raw value appropriate to the field's kind, or the ``UNSET`` sentinel.
    """
    if isinstance(field, _SPECIALISED):
        return UNSET

    name = field.name.lower()

    if _is_string_field(field):
        for tokens, producer in _TEXT_RULES:
            if _matches(name, tokens):
                return producer(ctx)
    elif _is_number_field(field):
        for tokens, producer in _NUMBER_RULES:
            if _matches(name, tokens):
                return producer(ctx)

    return UNSET
