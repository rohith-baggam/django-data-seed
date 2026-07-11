"""
A kitchen-sink app that exercises every field type and relationship the engine
claims to support. It lives under ``tests/`` so it never ships in the installed
package -- fixing the 0.4.x bug where ~25 test models landed in real databases.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UnknownField(models.Field):
    """A field type with no registered provider -- used to exercise the
    'unsupported field' reporting path. Stored as plain text."""

    def db_type(self, connection):
        return "text"


class Author(models.Model):
    # ? ``name`` / ``email`` / ``city`` all lean on field-name inference.
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=80)
    website = models.URLField(blank=True)
    bio = models.TextField(blank=True, null=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=120, unique=True)
    country = models.CharField(max_length=60)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)


class Tag(models.Model):
    name = models.SlugField(max_length=40, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    isbn = models.CharField(max_length=13, unique=True)
    summary = models.TextField(blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    pages = models.PositiveIntegerField()
    rating = models.FloatField(null=True, blank=True)
    published = models.DateField()
    created_at = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    publisher = models.ForeignKey(
        Publisher, on_delete=models.SET_NULL, null=True, blank=True, related_name="books"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="books")
    metadata = models.JSONField(default=dict, blank=True)


class Profile(models.Model):
    # ? OneToOne must always get its own fresh, unshared parent.
    author = models.OneToOneField(Author, on_delete=models.CASCADE, related_name="profile")
    twitter = models.CharField(max_length=50, blank=True)
    joined = models.DateTimeField()


class Category(models.Model):
    # ? Self-referential FK -- category tree.
    name = models.CharField(max_length=60)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )


class Ticket(models.Model):
    """Exercises multi-column uniqueness (a total UniqueConstraint)."""

    class Section(models.TextChoices):
        LEFT = "L", "Left"
        RIGHT = "R", "Right"

    section = models.CharField(max_length=1, choices=Section.choices)
    number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["section", "number"], name="uniq_section_number")
        ]


class Document(models.Model):
    """Exercises the File/Image field providers."""

    attachment = models.FileField(upload_to="docs/")
    thumbnail = models.ImageField(upload_to="thumbs/", blank=True, null=True)


class Widget(models.Model):
    """Has a nullable field with no provider -- reported, then left NULL."""

    name = models.CharField(max_length=40)
    gizmo = UnknownField(null=True, blank=True)


class Order(models.Model):
    """Three lifecycle datetimes -- coherence should order them."""

    reference = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    shipped_at = models.DateTimeField()
    delivered_at = models.DateTimeField()


class Contact(models.Model):
    """Name fields that coherence should drive from one persona."""

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    full_name = models.CharField(max_length=120)


class Stamped(models.Model):
    """auto_now / auto_now_add columns must be left to Django, not generated."""

    label = models.CharField(max_length=30)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Node(models.Model):
    """One half of a nullable FK cycle (with Peer)."""

    label = models.CharField(max_length=20)
    peer = models.ForeignKey(
        "Peer", on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes"
    )


class Peer(models.Model):
    """The other half of the nullable FK cycle (with Node)."""

    label = models.CharField(max_length=20)
    node = models.ForeignKey(
        Node, on_delete=models.SET_NULL, null=True, blank=True, related_name="peers"
    )


class Everything(models.Model):
    """Broad field-type coverage for the provider tests."""

    identifier = models.UUIDField()
    small = models.SmallIntegerField()
    big = models.BigIntegerField()
    positive = models.PositiveIntegerField()
    positive_small = models.PositiveSmallIntegerField()
    positive_big = models.PositiveBigIntegerField()
    ratio = models.FloatField()
    span = models.DurationField()
    clock = models.TimeField()
    ip_v6_only = models.GenericIPAddressField(protocol="IPv6")
    ip_v4_only = models.GenericIPAddressField(protocol="IPv4")
    blob = models.BinaryField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    payload = models.JSONField(default=dict)
