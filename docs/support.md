# Supported versions

[![CI](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml/badge.svg?branch=v-1.0.0)](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml)

## Python & Django

`django-data-seed` supports the actively-maintained Python and Django releases.

| | Versions |
|---|---|
| **Python** | 3.10, 3.11, 3.12, 3.13, 3.14 |
| **Django** | 4.0, 4.1, 4.2 (LTS), 5.0, 5.1, 5.2 (LTS), 6.0 |

The Python floor is 3.10 (required by Mimesis). Each Django release is paired
with a Python version it officially supports.

## Tested in continuous integration

Every push runs the matrix below on GitHub Actions — the green
[CI badge](https://github.com/rohith-baggam/django-data-seed/actions/workflows/ci.yml)
above is the live proof. The full suite runs on each cell, plus a `ruff` lint job
and a "build the wheel and import it" smoke test.

| Python | Django | Database |
|---|---|---|
| 3.10 | 4.0 | SQLite |
| 3.10 | 4.2 | SQLite |
| 3.11 | 4.2 | SQLite |
| 3.11 | 4.2 (Mimesis 11 floor) | SQLite |
| 3.12 | 5.0 | SQLite |
| 3.12 | 5.1 | SQLite |
| 3.13 | 5.2 | SQLite |
| 3.12 | 5.2 | **PostgreSQL 16** |
| 3.12 | 5.2 | **MySQL 8.4** |

So every run verifies **Python 3.10–3.13** against **Django 4.0–5.2** on
**SQLite, PostgreSQL, and MySQL**, and the oldest supported Mimesis (11).

!!! note "Python 3.14 and Django 6.0"
    Both are supported — the code is verified to run on them (full suite green on
    Python 3.13/3.14 + Django 6.0 locally) — but they are not currently part of
    the automated CI matrix.

## Databases

Everything goes through Django's ORM, so the core works on any backend Django
can talk to. "Supported" means tested in CI and quirk-handled:

| Engine | Driver (extra) | Status |
|---|---|---|
| SQLite | built-in | First-class (CI) |
| PostgreSQL | `django-data-seed[postgres]` | First-class (CI) |
| MySQL | `django-data-seed[mysql]` | Supported (CI) |
| MariaDB | `django-data-seed[mysql]` | Supported (CI) |
| SQL Server | `django-data-seed[mssql]` | Supported |
| Oracle | `django-data-seed[oracle]` | Best-effort |

The engine adapts to backend capabilities it discovers during the
[pre-flight probe](features/preflight.md) — native UUID/JSON support, whether
`bulk_create` can return primary keys, datetime precision, and `USE_TZ`.

!!! note "Backend-specific fields"
    PostgreSQL-only fields (`ArrayField`, `HStoreField`, range fields) and GIS
    geometry fields are on the roadmap for a later release. On a backend that
    can't store a given field, the engine reports it rather than crashing.

## Field types

Every standard Django field type is supported and generated with a valid,
constraint-honouring value. See **[Data generation](features/generation.md)** for
the full list and **[File & media fields](features/files.md)** for File/Image/
FilePath handling. Django 5's `GeneratedField` is recognised and left for the
database to compute.
