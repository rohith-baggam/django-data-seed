"""
Regression tests for the V2_IMPROVEMENTS_FIXES review.

One test (or more) per confirmed bug and gap: multi-DB uniqueness, the dry-run
progress leak, per-model isolation, CLI error wrapping, the QuerySet-override
N+1, composite uniqueness, unsupported-field reporting, file fields, coherence,
self-FK trees, and the relevant Part-C polish.
"""

import os
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext, isolate_apps

from django_data_seed import seed
from django_data_seed.engine.relations import generatable_fields
from django_data_seed.engine.runner import Runner, SeedConfig
from django_data_seed.engine.uniqueness import UniquenessTracker
from tests.testapp.models import (
    Author,
    Book,
    Category,
    Contact,
    Document,
    Node,
    Order,
    Peer,
    Stamped,
    Tag,
    Ticket,
    UnknownField,
    Widget,
)


class RecordingReporter:
    """Captures reporter callbacks so tests can assert on them."""

    def __init__(self):
        self.unsupported_report = {}
        self.closed = 0

    def preflight(self, results): ...
    def unsupported(self, report): self.unsupported_report = report
    def plan(self, order, count): ...
    def model_start(self, model, count): ...
    def tick(self, n=1): ...
    def model_done(self, result): ...
    def finished(self, result): ...
    def close(self): self.closed += 1


# --- A1: multi-database uniqueness -----------------------------------------


@pytest.mark.django_db(databases=["default", "secondary"])
def test_uniqueness_preload_respects_using():
    Author.objects.using("secondary").create(name="X", email="dup@example.com", city="C")

    field = Author._meta.get_field("email")
    secondary = UniquenessTracker(using="secondary")
    # ? The secondary tracker sees the secondary row and treats it as taken.
    assert secondary.reserve(Author, field, "dup@example.com") is False
    assert secondary.reserve(Author, field, "fresh@example.com") is True

    # ? The default connection has no such row -- the value is free there.
    default = UniquenessTracker(using="default")
    assert default.reserve(Author, field, "dup@example.com") is True


# --- A2: dry-run must not leak the progress display ------------------------


@pytest.mark.django_db
def test_dry_run_closes_progress_and_writes_nothing():
    reporter = RecordingReporter()
    result = seed("testapp.Author", count=5, dry_run=True, reporter=reporter)
    assert result.dry_run is True
    assert Author.objects.count() == 0
    assert reporter.closed >= 1  # ? close() ran -> nothing left hijacking stdout


# --- A3: one failing model must not abort the whole run --------------------


@pytest.mark.django_db
def test_one_failing_model_does_not_abort_the_run():
    def boom():
        raise RuntimeError("intentional generator failure")

    result = seed(
        ["testapp.Author", "testapp.Tag"],
        count=10,
        overrides={"testapp.Author": {"name": boom}},
    )
    by_label = {r.label: r for r in result.per_model}
    assert by_label["testapp.Author"].skipped is not None
    assert by_label["testapp.Tag"].skipped is None
    assert Tag.objects.count() == 10        # ? later model still seeded
    assert Author.objects.count() == 0      # ? failed model rolled back
    assert result.skipped                   # ? surfaced on the result


# --- A4: a bad CLI target yields a CommandError, not a traceback ------------


@pytest.mark.django_db
def test_bad_app_label_raises_command_error():
    with pytest.raises(CommandError):
        call_command("seeddata", "nosuchapp", verbosity=0)


@pytest.mark.django_db
def test_bad_model_label_raises_command_error():
    with pytest.raises(CommandError):
        call_command("seeddata", "testapp.NoSuchModel", verbosity=0)


# --- A5: a QuerySet FK override resolves once, not per row ------------------


@pytest.mark.django_db
def test_queryset_fk_override_is_not_n_plus_one():
    seed("testapp.Author", count=5)
    with CaptureQueriesContext(connection) as captured:
        seed("testapp.Book", count=25, overrides={"author": Author.objects.all()})
    author_selects = [
        q for q in captured.captured_queries
        if 'from "testapp_author"' in q["sql"].lower()
    ]
    # ? Old code did ~one SELECT per row; the pool is now resolved a handful of times.
    assert len(author_selects) <= 3
    assert Book.objects.count() == 25


# --- B1: composite (multi-column) uniqueness -------------------------------


@pytest.mark.django_db
def test_composite_unique_constraint_has_no_duplicates():
    # ? (section in {L,R}) x (number in 1..5) = 10 combinations; seed exactly 10.
    seed("testapp.Ticket", count=10)
    pairs = list(Ticket.objects.values_list("section", "number"))
    assert len(pairs) == 10
    assert len(set(pairs)) == 10


# --- B2: unsupported fields -------------------------------------------------


@pytest.mark.django_db
def test_unsupported_nullable_field_is_reported_and_left_null():
    reporter = RecordingReporter()
    seed("testapp.Widget", count=4, reporter=reporter)
    assert Widget.objects.count() == 4
    assert all(w.gizmo is None for w in Widget.objects.all())
    assert "testapp.Widget" in reporter.unsupported_report


def test_required_unsupported_field_is_flagged_required():
    # ? Defined via isolate_apps so it never needs a database table.
    from django.db import models as dj_models

    with isolate_apps("tests.testapp"):
        class ReqWidget(dj_models.Model):
            thing = UnknownField()  # not null, no default -> required + unsupported

            class Meta:
                app_label = "testapp"

        runner = Runner(SeedConfig())
        report = runner._analyze_unsupported([ReqWidget])
        assert report["testapp.ReqWidget"] == [("thing", True)]


# --- B3: file-field providers ----------------------------------------------


@pytest.mark.django_db
def test_file_fields_write_real_files():
    seed("testapp.Document", count=3)
    docs = list(Document.objects.all())
    # ? R2-5: files land under the field's own upload_to, not a hard-coded seed/.
    assert docs and all(d.attachment.name.startswith("docs/") for d in docs)
    for doc in docs:
        assert os.path.exists(doc.attachment.path)


@pytest.mark.django_db
def test_no_files_skips_writing_to_disk():
    seed("testapp.Document", count=2, make_files=False)
    for doc in Document.objects.all():
        assert doc.attachment.name.startswith("docs/")
        assert not os.path.exists(doc.attachment.path)


# --- B5: cross-field coherence ---------------------------------------------


@pytest.mark.django_db
def test_lifecycle_datetimes_are_ordered():
    seed("testapp.Order", count=25, seed=3)
    for order in Order.objects.all():
        assert order.created_at <= order.shipped_at <= order.delivered_at


@pytest.mark.django_db
def test_persona_fields_agree():
    seed("testapp.Contact", count=15, seed=3)
    for contact in Contact.objects.all():
        assert contact.full_name == f"{contact.first_name} {contact.last_name}"


# --- B6: self-FK trees + broken-cycle patch pass ---------------------------


@pytest.mark.django_db
def test_self_fk_forms_a_shallow_tree_not_all_roots():
    seed("testapp.Category", count=20, seed=7)
    children = [c for c in Category.objects.all() if c.parent_id is not None]
    assert len(children) >= 10                       # ? most rows got a parent
    assert all(c.parent_id < c.id for c in children)  # ? parent is an earlier row


@pytest.mark.django_db
def test_broken_nullable_cycle_edges_are_patched():
    seed(["testapp.Node", "testapp.Peer"], count=10, seed=1)
    assert Node.objects.count() == 10 and Peer.objects.count() == 10
    node_wired = Node.objects.filter(peer__isnull=False).count()
    peer_wired = Peer.objects.filter(node__isnull=False).count()
    # ? Whichever side had its FK forced NULL to break the cycle is fully wired
    # ? by the patch pass.
    assert max(node_wired, peer_wired) == 10


# --- C5: auto_now / auto_now_add are not generated -------------------------


def test_auto_now_fields_are_not_generated():
    names = {f.name for f in generatable_fields(Stamped)}
    assert "created" not in names
    assert "updated" not in names
    assert "label" in names


@pytest.mark.django_db
def test_auto_now_model_still_seeds():
    seed("testapp.Stamped", count=3)
    assert Stamped.objects.count() == 3
    assert all(s.created is not None and s.updated is not None for s in Stamped.objects.all())


# --- C2: dry-run JSON emits the plan ---------------------------------------


@pytest.mark.django_db
def test_dry_run_json_emits_plan():
    import json

    out = StringIO()
    call_command(
        "seeddata", "testapp.Book", "--count", "5", "--dry-run", "--format", "json",
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    assert payload["dry_run"] is True
    assert "testapp.Book" in payload["plan"]["order"]


# --- C8: nullable FKs get exercised as NULL --------------------------------


@pytest.mark.django_db
def test_high_null_probability_nulls_optional_fks():
    seed("testapp.Author", count=10)
    seed("testapp.Publisher", count=10)
    seed("testapp.Book", count=30, null_probability=0.9, seed=5)
    # ? publisher is a nullable FK; with p=0.9 many rows should have no publisher.
    assert Book.objects.filter(publisher__isnull=True).exists()


# --- R2-1: self-FK patch pass must not touch pre-existing rows --------------


@pytest.mark.django_db
def test_self_fk_patch_leaves_pre_existing_rows_untouched():
    # ? Curated fixtures: 10 root categories a user created deliberately.
    curated = [Category.objects.create(name=f"curated-{i}", parent=None) for i in range(10)]
    seed("testapp.Category", count=5, seed=1)

    for row in curated:
        row.refresh_from_db()
        assert row.parent_id is None, "a pre-existing self-FK row was rewritten"


# --- R2-2: forced-null (broken cycle) patch must not touch pre-existing rows -


@pytest.mark.django_db
def test_forced_null_patch_leaves_pre_existing_nulls_untouched():
    orphan_node = Node.objects.create(label="deliberately-orphan", peer=None)
    orphan_peer = Peer.objects.create(label="deliberately-orphan", node=None)

    seed(["testapp.Node", "testapp.Peer"], count=5, seed=2)

    orphan_node.refresh_from_db()
    orphan_peer.refresh_from_db()
    assert orphan_node.peer_id is None, "a pre-existing NULL FK was patched"
    assert orphan_peer.node_id is None, "a pre-existing NULL FK was patched"


# --- R2-4: atomic="all" is all-or-nothing ----------------------------------


def _boom():
    raise ValueError("boom")


@pytest.mark.django_db
def test_atomic_all_rolls_back_everything_on_a_failure():
    # ? Author seeds first, then Tag fails via a raising override.
    with pytest.raises(ValueError):
        seed(
            ["testapp.Author", "testapp.Tag"],
            count=4,
            atomic="all",
            overrides={"testapp.Tag": {"name": _boom}},
        )
    # ? Because it was one transaction, Author's rows were rolled back too.
    assert Author.objects.count() == 0


@pytest.mark.django_db
def test_atomic_model_isolates_the_failure_and_keeps_the_rest():
    result = seed(
        ["testapp.Author", "testapp.Tag"],
        count=4,
        atomic="model",
        overrides={"testapp.Tag": {"name": _boom}},
    )
    # ? Default isolation: Author survives, Tag is recorded as skipped.
    assert Author.objects.count() == 4
    assert any(r.skipped for r in result.per_model)


# --- R2-7: discarded composite retries don't burn single-column uniques -----


@pytest.mark.django_db
def test_release_returns_a_reserved_value_to_the_pool():
    tracker = UniquenessTracker()
    field = Author._meta.get_field("email")

    assert tracker.reserve(Author, field, "a@example.com") is True
    assert tracker.reserve(Author, field, "a@example.com") is False  # ? now taken
    tracker.release(Author, field, "a@example.com")
    assert tracker.reserve(Author, field, "a@example.com") is True  # ? freed again
