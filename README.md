# django-data-seed

[![CI](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml/badge.svg?branch=v-1.0.0)](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/django-data-seed.svg)](https://pypi.org/project/django-data-seed/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%E2%80%93%203.14-blue.svg)](https://pypi.org/project/django-data-seed/)
[![Django versions](https://img.shields.io/badge/django-4.0%20%E2%80%93%206.0-0C4B33.svg)](https://pypi.org/project/django-data-seed/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Fill your entire Django database with realistic, valid test data — in one command, with zero configuration.**

Every Django project hits the same wall: you need data to build against. So you
click through the admin for twenty minutes, or hand-write fixtures, or maintain a
factory for every single model — and you *still* end up with `test test` and
`a@a.com` everywhere, which makes demos look fake and lets real bugs hide.

**django-data-seed** does it for you. Point it at your project and it reads your
models, works out the right order to fill them, generates believable data that
respects every field's rules, and bulk-inserts the lot — in seconds.

```bash
pip install django-data-seed
python manage.py seeddata --count 20 --seed 42
```

```text
Pre-flight
  ✔ Database: postgresql (JSON ✓, bulk-returns-pk ✓)
  ✔ Migrations: all applied
  ✔ Schema: 14 models in sync
Seed plan — 20 rows per model
├── shop.Author
├── shop.Publisher
└── shop.Book
✨ 280 rows across 14 models in 0.4s (seed 42)
```

That's the whole thing. No factories, no fixtures, no configuration.

---

## Features

| Feature | What it does for you |
|---|---|
| **Zero-config generation** | Reads your models and fills every field type with a valid value — nothing to write. |
| **Realistic values** | A column named `city` gets a real city, `email` a real address, `price` a believable amount — not lorem ipsum. |
| **Correct relationships** | Seeds parents before children and **reuses** existing rows, instead of creating a fresh parent for every child. |
| **Coherent rows** | A row makes sense with itself: `created ≤ updated ≤ shipped` dates, one person behind the name/email, one place behind the city/zip. |
| **Reliable uniqueness** | Honours `unique` and `unique_together` / `UniqueConstraint` without hitting duplicate errors. |
| **Pre-flight safety** | Refuses to run against a stale schema — it flags unapplied migrations or model drift *before* writing a row. |
| **Bulk speed** | `bulk_create`, batched — a hundred thousand rows in seconds. |
| **Reproducible** | `--seed 42` produces the exact same data every run — for teammates, CI, and bug reports. |
| **CLI *and* Python API** | Watch it run in the terminal, or call `seed()` from your scripts and tests. |

## Supported versions

| | Supported |
|---|---|
| **Python** | 3.10, 3.11, 3.12, 3.13, 3.14 |
| **Django** | 4.0 → 6.0 (every release, including the 4.2 and 5.2 LTS) |
| **Databases** | SQLite, PostgreSQL, MySQL / MariaDB, SQL Server |

Every push is tested on GitHub Actions across **Python 3.10–3.13 × Django 4.0–5.2
on SQLite, PostgreSQL, and MySQL** — the [CI badge](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml)
above is the live proof.

## Dependencies

Installing the package pulls in just **three** small runtime dependencies:

| Package | Why it's needed |
|---|---|
| `Django >= 4.0` | The framework the app plugs into. |
| `mimesis >= 11` | Generates the fake data — fast and locale-aware. |
| `rich >= 13` | Draws the progress bars and summary tables in the CLI. |

Database drivers are **optional extras**, so you only install what you use:

```bash
pip install django-data-seed              # core — SQLite works out of the box
pip install django-data-seed[postgres]    # PostgreSQL (psycopg)
pip install django-data-seed[mysql]       # MySQL & MariaDB (mysqlclient)
```

## How to configure it in your project

Three steps — that's the entire setup.

**1. Install**

```bash
pip install django-data-seed
```

**2. Add it to `INSTALLED_APPS`**

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_data_seed",
]
```

**3. Seed**

```bash
python manage.py seeddata --count 20 --seed 42
```

### Using it

```bash
python manage.py seeddata                      # every model, 10 rows each
python manage.py seeddata shop.Book --count 50 # just one model
python manage.py seeddata --dry-run            # preview the plan, write nothing
python manage.py seeddata --locale de_DE       # localised data
```

Or from Python — handy in scripts and tests:

```python
from django_data_seed import seed

seed("shop.Book", count=50, seed=42)   # reproducible
seed(count=25)                         # the whole project
```

---

## 📖 Full documentation

The README is the quick tour. For the complete guide — every CLI flag, the Python
API, how foreign-key strategies and coherence work, custom overrides, and the
0.4 → 1.0 migration notes — see the docs:

- **Documentation:** <https://rohith-baggam.github.io/django-data-seed/>
- **Source & issues:** <https://github.com/rohith-baggam/django-data-seed>

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file
for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any
changes.

## Support

For any issues or questions, open an issue on the
[GitHub repository](https://github.com/rohith-baggam/django-data-seed/issues).

## Author

**Rohith Baggam**

[LinkedIn](https://www.linkedin.com/in/rohith-baggam/) ·
[GitHub](https://github.com/rohith-baggam)
