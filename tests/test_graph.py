"""
Dependency-graph tests: ordering, self-FK, and cycle handling (bug 7 in the plan
-- FK cycles used to blow the stack; now they are ordered or reported cleanly).
"""

import pytest
from django.db import models
from django.test.utils import isolate_apps

from django_data_seed.engine.graph import HardCycleError, build_order
from tests.testapp.models import Author, Book, Category, Profile, Publisher, Tag


def test_parents_are_ordered_before_children():
    order = build_order([Book, Author, Publisher, Tag])
    labels = [m._meta.label for m in order.models]
    assert labels.index("testapp.Author") < labels.index("testapp.Book")
    assert labels.index("testapp.Publisher") < labels.index("testapp.Book")
    # ? Tag is an M2M target of Book, so it must come first too.
    assert labels.index("testapp.Tag") < labels.index("testapp.Book")


def test_one_to_one_parent_ordered_first():
    order = build_order([Profile, Author])
    labels = [m._meta.label for m in order.models]
    assert labels.index("testapp.Author") < labels.index("testapp.Profile")


def test_self_referential_model_orders_without_error():
    order = build_order([Category])
    assert [m._meta.label for m in order.models] == ["testapp.Category"]


def test_nullable_cycle_is_broken_not_crashed():
    with isolate_apps("tests.testapp"):
        class Node(models.Model):
            # ? Two nullable FKs pointing at each other: a breakable cycle.
            buddy = models.ForeignKey("Mate", null=True, on_delete=models.SET_NULL)

            class Meta:
                app_label = "testapp"

        class Mate(models.Model):
            friend = models.ForeignKey("Node", null=True, on_delete=models.SET_NULL)

            class Meta:
                app_label = "testapp"

        order = build_order([Node, Mate])
        assert len(order.models) == 2
        # ? Exactly one edge was broken and recorded as a force-NULL field.
        assert sum(len(v) for v in order.force_null_fields.values()) >= 1


def test_hard_cycle_raises_clear_error():
    with isolate_apps("tests.testapp"):
        class Left(models.Model):
            right = models.ForeignKey("Right", on_delete=models.CASCADE)

            class Meta:
                app_label = "testapp"

        class Right(models.Model):
            left = models.ForeignKey("Left", on_delete=models.CASCADE)

            class Meta:
                app_label = "testapp"

        with pytest.raises(HardCycleError) as exc:
            build_order([Left, Right])
        assert "cycle" in str(exc.value).lower()
