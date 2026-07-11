"""
A small demo store, chosen to show off what django-data-seed does with zero
configuration: field-name inference (``email``, ``first_name``, ``city``,
``price``), row coherence (an order's dates come out in order; a customer's name
and email agree), foreign-key reuse, a self-referential category tree, and M2M.

    cd example_project
    python manage.py makemigrations shop
    python manage.py migrate
    python manage.py seeddata --seed 42
"""

from django.db import models


class Category(models.Model):
    # ? Self-referential FK -> shallow tree after seeding.
    name = models.CharField(max_length=60)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        verbose_name_plural = "categories"


class Supplier(models.Model):
    company_name = models.CharField(max_length=120, unique=True)
    city = models.CharField(max_length=80)
    country = models.CharField(max_length=60)
    email = models.EmailField()


class Tag(models.Model):
    name = models.SlugField(max_length=40, unique=True)


class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISCONTINUED = "discontinued", "Discontinued"
        DRAFT = "draft", "Draft"

    name = models.CharField(max_length=120)
    sku = models.SlugField(max_length=40, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")


class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=80)


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    reference = models.SlugField(max_length=20, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField()
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
