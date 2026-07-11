# Getting started

## Install

```bash
pip install django-data-seed
```

SQLite works out of the box. For other databases, install the matching extra
(these just pull in the driver — see [Dependencies](dependencies.md)):

```bash
pip install django-data-seed[postgres]    # psycopg
pip install django-data-seed[mysql]       # mysqlclient (MySQL & MariaDB)
```

## Configure

Add the app to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_data_seed",
]
```

That's the entire setup. No other settings are required.

## Your first seed

```bash
# Every model in your project, 10 rows each:
python manage.py seeddata

# A specific model, 50 rows, reproducibly:
python manage.py seeddata shop.Book --count 50 --seed 42
```

You'll see a live pre-flight checklist, the seed plan as a dependency tree, a
progress bar, and a summary table:

```
Pre-flight
  ✔ Database: sqlite (JSON ✓, bulk-returns-pk ✓)
  ✔ Migrations: all applied
  ✔ Schema: 6 models in sync
Seed plan — 50 rows per model
└── shop.Book
✨ 50 rows across 1 model in 0.06s (seed 42)
```

## Preview before you write

`--dry-run` runs the pre-flight checks and prints the plan **without inserting a
single row** — a fast way to see the seed order and confirm your schema is in
sync:

```bash
python manage.py seeddata --dry-run
```

## From Python

Everything the command does is available as a function, so seeding fits into
scripts, data-migration steps, and tests:

```python
from django_data_seed import seed

seed("shop.Book", count=50, seed=42)   # one model, reproducible
seed(count=25)                         # the whole project
```

See the **[Python API](python-api.md)** for `seed()`, `SeedPlan`, and the
`SeedResult` it returns.

## A 30-second tour

```bash
python manage.py seeddata shop.Author --count 20        # seed parents first
python manage.py seeddata shop.Book --count 100         # books reuse those authors
python manage.py seeddata --exclude shop.AuditLog       # whole project minus one
python manage.py seeddata --strategy create             # fresh parents, not reuse
python manage.py seeddata --locale de_DE                # localised data
python manage.py seeddata --format json                 # machine-readable summary
```

Next: the **[Features](features/index.md)** section explains what's happening
under each of these.
