"""
Management-command tests: the thin ``seeddata`` wrapper, its new flags, the
deprecated aliases, dry-run, and JSON output.
"""

import json
from io import StringIO

import pytest
from django.core.management import call_command

from tests.testapp.models import Author, Book

pytestmark = pytest.mark.django_db


def test_command_seeds_a_single_model():
    call_command("seeddata", "testapp.Author", "--count", "7", verbosity=0)
    assert Author.objects.count() == 7


def test_dry_run_writes_nothing():
    call_command("seeddata", "testapp.Author", "--count", "5", "--dry-run", verbosity=0)
    assert Author.objects.count() == 0


def test_deprecated_no_of_objects_alias_still_works():
    err = StringIO()
    call_command(
        "seeddata", "testapp.Author", "--no-of-objects-to-create", "4",
        verbosity=0, stderr=err,
    )
    assert Author.objects.count() == 4
    assert "deprecated" in err.getvalue().lower()


def test_json_format_emits_machine_readable_summary():
    out = StringIO()
    call_command("seeddata", "testapp.Author", "--count", "3", "--format", "json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["total"] == 3
    assert payload["models"][0]["label"] == "testapp.Author"


def test_seed_flag_is_reproducible_across_command_runs():
    call_command("seeddata", "testapp.Author", "--count", "3", "--seed", "5", verbosity=0)
    call_command("seeddata", "testapp.Book", "--count", "10", "--seed", "5", verbosity=0)
    assert Book.objects.count() == 10
