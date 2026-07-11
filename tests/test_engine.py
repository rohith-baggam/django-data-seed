"""
End-to-end engine tests: the whole thing seeding a real (SQLite) database.

Covers the headline v2 promises -- FK reuse instead of row explosion (bug 8),
in-memory uniqueness (bug 17), every field type filled with a valid value,
timezone-aware datetimes, reproducibility from a seed, and clean ``full_clean``.
"""

import pytest

from django_data_seed import seed
from tests.testapp.models import (
    Author,
    Book,
    Category,
    Everything,
    Profile,
    Tag,
)

pytestmark = pytest.mark.django_db


def test_seed_single_model_creates_requested_count():
    seed("testapp.Author", count=15)
    assert Author.objects.count() == 15


def test_unique_fields_stay_unique():
    seed("testapp.Author", count=40)
    emails = list(Author.objects.values_list("email", flat=True))
    assert len(emails) == len(set(emails))


def test_fk_reuse_does_not_explode_parents():
    seed("testapp.Author", count=10)
    seed("testapp.Book", count=30)
    # ? All 30 books point at the 10 existing authors -- no fresh authors made.
    assert Author.objects.count() == 10
    assert Book.objects.count() == 30
    used_authors = set(Book.objects.values_list("author_id", flat=True))
    assert used_authors.issubset(set(Author.objects.values_list("id", flat=True)))


def test_fk_create_strategy_makes_fresh_parents():
    seed("testapp.Book", count=5, strategy="create")
    # ? create strategy makes a brand-new author per book (plus none pre-existed).
    assert Author.objects.count() >= 5


def test_one_to_one_parents_are_unique():
    seed("testapp.Profile", count=8)
    author_ids = list(Profile.objects.values_list("author_id", flat=True))
    assert len(author_ids) == len(set(author_ids)) == 8


def test_choices_field_only_uses_valid_choices():
    seed("testapp.Author", count=5)
    seed("testapp.Book", count=25)
    valid = set(Book.Status.values)
    assert set(Book.objects.values_list("status", flat=True)).issubset(valid)


def test_decimal_and_ip_fields_are_valid_after_full_clean():
    seed("testapp.Everything", count=20)
    for row in Everything.objects.all():
        row.full_clean(exclude=["id"])  # ? no validation errors -> every field legal


def test_datetimes_are_timezone_aware():
    seed("testapp.Book", count=3)
    for book in Book.objects.all():
        assert book.created_at.tzinfo is not None


def test_whole_project_seed_runs_clean():
    result = seed(count=6)
    labels = {r.label for r in result.per_model}
    # ? Every kitchen-sink model got seeded.
    assert "testapp.Book" in labels
    assert result.total > 0
    assert Book.objects.count() == 6
    assert Category.objects.count() == 6


def test_m2m_gets_attached_when_targets_exist():
    # ? Fixed seed so the (otherwise random) attach count is deterministic.
    seed(count=8, seed=1)
    assert Tag.objects.count() == 8
    # ? Some books should have picked up tags via the auto through table.
    attached = sum(book.tags.count() for book in Book.objects.all())
    assert attached > 0


def test_run_is_reproducible_with_a_seed():
    seed("testapp.Everything", count=6, seed=99)
    first = sorted(Everything.objects.values_list("small", flat=True))
    Everything.objects.all().delete()

    seed("testapp.Everything", count=6, seed=99)
    second = sorted(Everything.objects.values_list("small", flat=True))
    assert first == second


def test_null_probability_zero_never_nulls():
    seed("testapp.Author", count=20, null_probability=0.0)
    # ? bio is nullable; with p=0 it must always be filled.
    assert not Author.objects.filter(bio__isnull=True).exists()


def test_name_inference_fills_email_shaped_values():
    seed("testapp.Author", count=5)
    assert all("@" in e for e in Author.objects.values_list("email", flat=True))
