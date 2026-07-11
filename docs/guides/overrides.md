# Guide: custom overrides

The default output is realistic, but sometimes you need a specific field to hold
specific values — a curated set of product names, a fixed status, a foreign key
drawn from a particular queryset. Overrides let you pin **only** those fields and
let the engine generate everything else.

Overrides are a Python-API feature (`seed(..., overrides=...)`).

## Override shapes

| You pass | The engine does |
|---|---|
| a **value** | uses it as-is for every row |
| a **callable** | calls it per row for a fresh value |
| a **`range`** | samples an item from it |
| a **list/tuple** | samples an item from it |
| a **`QuerySet`** (for an FK) | uses it as a reuse pool, resolved once |
| a **model instance / pk** (for an FK) | points every row at it |

## Example

```python
import random
from shop.models import Book, Author

REAL_TITLES = ["The Pragmatic Programmer", "Clean Code", "Refactoring"]

seed(Book, count=50, overrides={
    "title": lambda: random.choice(REAL_TITLES),  # curated names
    "price": range(5, 100),                        # sampled 5–99
    "status": "published",                         # constant
    "author": Author.objects.filter(active=True),  # FK reuse pool
})
```

Everything not listed — slug, ISBN, dates, description, other FKs — is still
generated and constraint-checked as usual.

## Single model vs several

For a single target model, `overrides` is a `{field_name: override}` map (as
above). When you seed several models at once, key the overrides by model label:

```python
seed(["shop.Book", "shop.Author"], count=20, overrides={
    "shop.Book": {"status": "published"},
    "shop.Author": {"is_active": True},
})
```

## Overrides and uniqueness

Overrides on a **unique** column still go through the uniqueness tracker, so a
sampled/generated override won't produce duplicates. If your override pool is
smaller than `count` for a unique column, generation will exhaust — give it a
pool at least as large as the row count.
