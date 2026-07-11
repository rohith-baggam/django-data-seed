"""
Provider-level tests: MRO dispatch and per-field type correctness.

These are the regression receipts for bugs 4, 10, 12, 13 in the v2 plan --
URL/Slug fields resolving correctly, decimals honouring ``max_digits``, IP
protocol respected, unique text without ``max_length`` not crashing.
"""

import datetime
import uuid
from decimal import Decimal

import pytest
from django.db import models

from django_data_seed.engine import providers
from django_data_seed.engine.context import GenContext


@pytest.fixture
def ctx():
    return GenContext(seed=1234)


def gen(field, ctx):
    field.set_attributes_from_name(field.name or "field")
    return providers.generate_type_value(field, ctx)


def test_slugfield_resolves_to_slug_provider_not_charfield(ctx):
    # ? SlugField subclasses CharField; MRO dispatch must pick the slug provider.
    field = models.SlugField(name="slug")
    value = gen(field, ctx)
    assert " " not in value
    assert value == value.lower()


def test_urlfield_produces_a_url_not_a_sentence(ctx):
    field = models.URLField(name="link")
    value = gen(field, ctx)
    assert value.startswith(("http://", "https://"))


def test_emailfield_produces_an_email(ctx):
    field = models.EmailField(name="email")
    assert "@" in gen(field, ctx)


def test_decimalfield_respects_max_digits_and_places(ctx):
    field = models.DecimalField(name="amount", max_digits=5, decimal_places=2)
    value = gen(field, ctx)
    assert isinstance(value, Decimal)
    sign, digits, exponent = value.as_tuple()
    assert len(digits) <= 5
    assert -exponent <= 2


def test_generic_ip_respects_ipv6_protocol(ctx):
    field = models.GenericIPAddressField(name="addr", protocol="IPv6")
    value = gen(field, ctx)
    assert ":" in value  # ? IPv6 addresses are colon-separated.


def test_generic_ip_respects_ipv4_protocol(ctx):
    field = models.GenericIPAddressField(name="addr", protocol="IPv4")
    value = gen(field, ctx)
    assert value.count(".") == 3


def test_integer_bounds_are_respected_for_positive_small(ctx):
    field = models.PositiveSmallIntegerField(name="qty")
    for _ in range(50):
        value = gen(field, ctx)
        assert 0 <= value <= 32767


def test_uuidfield_is_a_uuid(ctx):
    field = models.UUIDField(name="identifier")
    assert isinstance(gen(field, ctx), uuid.UUID)


def test_duration_and_time_types(ctx):
    assert isinstance(gen(models.DurationField(name="span"), ctx), datetime.timedelta)
    assert isinstance(gen(models.TimeField(name="clock"), ctx), datetime.time)


def test_unsupported_field_type_returns_none(ctx):
    class WeirdField(models.Field):
        pass

    assert providers.resolve_provider(WeirdField(name="x")) is None


def test_custom_field_inherits_parent_provider_via_mro(ctx):
    class UpperCharField(models.CharField):
        pass

    field = UpperCharField(name="title", max_length=40)
    field.set_attributes_from_name("title")
    assert isinstance(providers.generate_type_value(field, ctx), str)
