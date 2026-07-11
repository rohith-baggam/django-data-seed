"""
Field-type providers and the registry that dispatches to them.

The single most important fix over 0.4.x lives here: dispatch walks the field's
real MRO and the *most specific* registered class wins by construction. A
``SlugField`` is a ``CharField`` subclass, so it resolves to the slug provider
before it can ever be claimed by the char provider -- no more slugs full of
spaces or URL columns full of sentences. A custom field nobody registered
inherits its parent's provider for free.

Register a provider with the ``@provider(SomeField)`` decorator. The callable
receives ``(field, ctx)`` and returns a raw value; clamping to the column
happens later in the generator pipeline.
"""

from __future__ import annotations

import datetime
import os
import secrets
import tempfile
import uuid
from collections.abc import Callable
from decimal import Decimal

from django.db import models
from django.utils import timezone

from . import constraints
from .context import GenContext

# ? The registry maps a concrete Django field class to its generator callable.
ProviderFn = Callable[[models.Field, GenContext], object]
_REGISTRY: dict[type[models.Field], ProviderFn] = {}


def provider(*field_classes: type[models.Field]) -> Callable[[ProviderFn], ProviderFn]:
    """
    Registers a callable as the generator for one or more Django field classes.

    Args:
        - field_classes: The field classes this provider should handle.

    Returns:
        - A decorator that records the callable and returns it unchanged.
    """

    def register(fn: ProviderFn) -> ProviderFn:
        for field_class in field_classes:
            _REGISTRY[field_class] = fn
        return fn

    return register


def resolve_provider(field: models.Field) -> ProviderFn | None:
    """
    Finds the most specific registered provider for a field by walking its MRO.

    Args:
        - field: The model field an instance value is needed for.

    Returns:
        - The matching provider callable, or ``None`` when no ancestor class is
          registered (the caller then reports the field as unsupported).
    """
    for klass in type(field).__mro__:
        if klass in _REGISTRY:
            return _REGISTRY[klass]
    return None


def generate_type_value(field: models.Field, ctx: GenContext):
    """
    Runs the type provider for ``field`` and returns its raw value.

    Args:
        - field: The model field to generate for.
        - ctx: The active generation context.

    Returns:
        - A raw, type-correct value, or ``None`` when the field type is
          unsupported.
    """
    fn = resolve_provider(field)
    if fn is None:
        return None
    return fn(field, ctx)


def is_supported(field: models.Field) -> bool:
    """Whether any registered provider covers this field's type."""
    return resolve_provider(field) is not None


# ---------------------------------------------------------------------------
# * Text-flavoured fields. Order of registration does not matter -- dispatch is
# * by MRO specificity, not by list position.
# ---------------------------------------------------------------------------


@provider(models.CharField)
def CharField(field: models.CharField, ctx: GenContext) -> str:
    """Short human text sized to the field's ``max_length``."""
    max_length = field.max_length or 50
    if max_length <= 12:
        value = ctx.text.word()
    elif max_length <= 60:
        value = ctx.text.title() if ctx.smart() else ctx.text.word()
    else:
        value = ctx.text.sentence()
    return constraints.clamp_length(value, field)


@provider(models.TextField)
def TextField(field: models.TextField, ctx: GenContext) -> str:
    """A short paragraph for long-form text columns."""
    value = ctx.text.text(quantity=ctx.rng.randint(2, 4))
    return constraints.clamp_length(value, field)


@provider(models.EmailField)
def EmailField(field: models.EmailField, ctx: GenContext) -> str:
    """A realistic email address."""
    return constraints.clamp_length(ctx.person.email(), field)


@provider(models.SlugField)
def SlugField(field: models.SlugField, ctx: GenContext) -> str:
    """A hyphenated slug -- never with the spaces the char provider would leave."""
    return constraints.clamp_length(ctx.internet.slug(), field)


@provider(models.URLField)
def URLField(field: models.URLField, ctx: GenContext) -> str:
    """A well-formed URL."""
    return constraints.clamp_length(ctx.internet.url(), field)


@provider(models.GenericIPAddressField)
def GenericIPAddressField(field: models.GenericIPAddressField, ctx: GenContext) -> str:
    """
    An IP address that respects the field's ``protocol`` -- IPv4, IPv6, or a
    random pick when the field allows both.
    """
    protocol = (getattr(field, "protocol", "both") or "both").lower()
    if protocol == "ipv6":
        return ctx.internet.ip_v6()
    if protocol == "ipv4":
        return ctx.internet.ip_v4()
    return ctx.internet.ip_v6() if ctx.rng.random() < 0.5 else ctx.internet.ip_v4()


@provider(models.UUIDField)
def UUIDField(field: models.UUIDField, ctx: GenContext) -> uuid.UUID:
    """A version-4 UUID drawn from the seeded RNG so runs stay reproducible."""
    return uuid.UUID(int=ctx.rng.getrandbits(128), version=4)


# ---------------------------------------------------------------------------
# * Numeric fields.
# ---------------------------------------------------------------------------


@provider(
    models.IntegerField,
    models.SmallIntegerField,
    models.BigIntegerField,
    models.PositiveIntegerField,
    models.PositiveSmallIntegerField,
    models.PositiveBigIntegerField,
)
def IntegerField(field: models.IntegerField, ctx: GenContext) -> int:
    """An integer inside the field's legal, validator-aware range."""
    low, high = constraints.integer_bounds(field)
    return ctx.rng.randint(low, high)


@provider(models.FloatField)
def FloatField(field: models.FloatField, ctx: GenContext) -> float:
    """A float inside the field's legal range."""
    low, high = constraints.validator_bounds(field)
    low = -1000.0 if low is None else float(low)
    high = 1000.0 if high is None else float(high)
    if low > high:
        low, high = high, low
    return round(ctx.rng.uniform(low, high), 4)


@provider(models.DecimalField)
def DecimalField(field: models.DecimalField, ctx: GenContext) -> Decimal:
    """
    A decimal that honours ``max_digits`` and ``decimal_places`` -- the old
    engine computed these and then threw them away.
    """
    max_digits, decimal_places = constraints.decimal_params(field)
    whole_digits = max_digits - decimal_places

    v_low, v_high = constraints.validator_bounds(field)
    if v_low is not None or v_high is not None:
        low = float(v_low) if v_low is not None else 0.0
        high = float(v_high) if v_high is not None else (10**whole_digits - 1)
        raw = Decimal(str(ctx.rng.uniform(low, high)))
    elif ctx.smart():
        # ? Money-ish columns look right when they follow a log-normal curve.
        centre = min(10 ** max(whole_digits - 1, 0), 500)
        raw = Decimal(str(ctx.lognormal(mean=centre)))
    else:
        raw = Decimal(str(ctx.rng.uniform(0, 10**whole_digits - 1)))

    return constraints.quantize_decimal(raw, max_digits, decimal_places)


@provider(models.BooleanField)
def BooleanField(field: models.BooleanField, ctx: GenContext) -> bool:
    """A boolean, gently biased toward ``True`` like most real flags."""
    return ctx.rng.random() < (0.6 if ctx.smart() else 0.5)


# ---------------------------------------------------------------------------
# * Temporal fields. Timestamps come out timezone-aware when Django's USE_TZ is
# * on, which the 0.4.x code never accounted for.
# ---------------------------------------------------------------------------


@provider(models.DateTimeField)
def DateTimeField(field: models.DateTimeField, ctx: GenContext) -> datetime.datetime:
    """A datetime within the last few years, aware or naive per ``USE_TZ``."""
    value = ctx.datetime.datetime(start=timezone.now().year - 3, end=timezone.now().year)
    if ctx.use_tz and timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_default_timezone())
    elif not ctx.use_tz and timezone.is_aware(value):
        value = timezone.make_naive(value)
    return value


@provider(models.DateField)
def DateField(field: models.DateField, ctx: GenContext) -> datetime.date:
    """A recent calendar date."""
    return ctx.datetime.date(start=timezone.now().year - 3, end=timezone.now().year)


@provider(models.TimeField)
def TimeField(field: models.TimeField, ctx: GenContext) -> datetime.time:
    """A time of day, biased toward business hours under the realism layer."""
    if ctx.smart():
        hour = ctx.rng.choices(range(24), weights=_BUSINESS_HOUR_WEIGHTS, k=1)[0]
    else:
        hour = ctx.rng.randint(0, 23)
    return datetime.time(hour, ctx.rng.randint(0, 59), ctx.rng.randint(0, 59))


@provider(models.DurationField)
def DurationField(field: models.DurationField, ctx: GenContext) -> datetime.timedelta:
    """A span from a few minutes up to a couple of weeks."""
    return datetime.timedelta(
        days=ctx.rng.randint(0, 14),
        hours=ctx.rng.randint(0, 23),
        minutes=ctx.rng.randint(0, 59),
        seconds=ctx.rng.randint(0, 59),
    )


# ? Rough weighting for a working day -- quiet overnight, busy 9-to-6.
_BUSINESS_HOUR_WEIGHTS = [
    1, 1, 1, 1, 1, 1, 2, 4, 7, 9, 10, 10, 9, 9, 10, 10, 8, 6, 4, 3, 2, 2, 1, 1
]


# ---------------------------------------------------------------------------
# * Binary and structured fields.
# ---------------------------------------------------------------------------


@provider(models.BinaryField)
def BinaryField(field: models.BinaryField, ctx: GenContext) -> bytes:
    """A handful of random bytes, respecting ``max_length`` when present."""
    length = min(field.max_length or 16, 32)
    return secrets.token_bytes(length)


@provider(models.JSONField)
def JSONField(field: models.JSONField, ctx: GenContext) -> dict:
    """A small, realistic nested document."""
    return {
        "id": str(uuid.UUID(int=ctx.rng.getrandbits(128), version=4)),
        "label": ctx.text.word(),
        "active": ctx.rng.random() < 0.7,
        "score": ctx.numeric.integer_number(0, 100),
        "tags": ctx.text.words(quantity=ctx.rng.randint(1, 3)),
    }


# ---------------------------------------------------------------------------
# * File fields. These write a tiny *real* file into ``MEDIA_ROOT/seed/`` so the
# * stored path actually points at something, and return the relative name the
# * column stores. ``--no-files`` (ctx.make_files=False) returns a name without
# * touching the disk, so models with a required file column still seed.
# ---------------------------------------------------------------------------

# ? The smallest valid PNG: a single transparent 1x1 pixel.
_ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
    b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _media_root(ctx: GenContext) -> str:
    """The base media directory seeded files are written under."""
    root = ctx.media_root
    if not root:
        from django.conf import settings

        root = getattr(settings, "MEDIA_ROOT", "") or os.path.join(
            tempfile.gettempdir(), "django_data_seed_media"
        )
    return str(root)


def _upload_prefix(field: models.Field) -> str:
    """
    The directory (relative to MEDIA_ROOT) a file column stores into.

    A string ``upload_to`` is honoured so files land where the app looks for
    them; a callable ``upload_to`` (which needs a real instance and filename we
    don't have yet) falls back to ``seed/``. Either way everything stays under
    ``MEDIA_ROOT``.
    """
    upload_to = getattr(field, "upload_to", "") or ""
    if isinstance(upload_to, str) and upload_to.strip("/"):
        return upload_to.strip("/").replace("\\", "/") + "/"
    return "seed/"


def _write_seed_file(field: models.Field, ctx: GenContext, suffix: str, payload: bytes) -> str:
    """
    Writes ``payload`` under ``MEDIA_ROOT/<upload_to>/`` and returns the relative
    name the column stores. With ``make_files`` off, returns the name only.
    """
    prefix = _upload_prefix(field)
    token = "".join(ctx.rng.choice("0123456789abcdef") for _ in range(12))
    name = f"{prefix}{token}{suffix}"
    if ctx.make_files:
        directory = os.path.join(_media_root(ctx), *prefix.strip("/").split("/"))
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"{token}{suffix}"), "wb") as handle:
            handle.write(payload)
    return name


@provider(models.FileField)
def FileField(field: models.FileField, ctx: GenContext) -> str:
    """A tiny text file under the field's ``upload_to``; returns its stored name."""
    return _write_seed_file(field, ctx, ".txt", b"django-data-seed sample file\n")


@provider(models.ImageField)
def ImageField(field: models.ImageField, ctx: GenContext) -> str:
    """A real 1x1 PNG under the field's ``upload_to``; returns its stored name."""
    return _write_seed_file(field, ctx, ".png", _ONE_PIXEL_PNG)


@provider(models.FilePathField)
def FilePathField(field: models.FilePathField, ctx: GenContext) -> str:
    """
    A path for a ``FilePathField``. When the configured directory exists and
    holds matching files we pick a real one; otherwise we synthesise a path.
    """
    directory = getattr(field, "path", None)
    if directory and os.path.isdir(directory):
        try:
            candidates = [
                entry for entry in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, entry))
            ]
        except OSError:
            candidates = []
        if candidates:
            return os.path.join(directory, ctx.rng.choice(candidates))
    base = directory or tempfile.gettempdir()
    token = "".join(ctx.rng.choice("0123456789abcdef") for _ in range(8))
    return constraints.clamp_length(os.path.join(base, f"{token}.txt"), field)


def field_is_supported(field: models.Field) -> bool:
    """
    Whether the engine can produce a value for a *scalar* field -- either a
    registered type provider covers it, or it carries ``choices`` (which the
    generator can always satisfy regardless of the underlying type).
    """
    if resolve_provider(field) is not None:
        return True
    return bool(constraints.choice_values(field))
