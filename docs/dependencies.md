# Dependencies

`django-data-seed` keeps its runtime footprint deliberately small: installing it
pulls in **three** packages and nothing else.

## Runtime dependencies

| Package | Version | Why it's here |
|---|---|---|
| [Django](https://www.djangoproject.com/) | `>=4.0` | The framework the app plugs into. |
| [Mimesis](https://mimesis.name/) | `>=11` | The data generator — fast, typed, locale-aware. Replaces Faker (see [Faker vs Mimesis](background/faker-vs-mimesis.md)). |
| [rich](https://rich.readthedocs.io/) | `>=13` | The animated CLI: pre-flight checklist, progress dashboard, summary tables. |

That's it — no `pandas`, no `numpy`, no ML libraries. The statistical realism
(distributions, temporal shapes) is built on the Python standard library.

## Optional extras

Database drivers and dev tooling are **optional**, so you only install what you
use:

```bash
pip install django-data-seed              # core (SQLite works out of the box)
pip install django-data-seed[postgres]    # psycopg
pip install django-data-seed[mysql]       # mysqlclient (MySQL & MariaDB)
pip install django-data-seed[mssql]       # mssql-django
pip install django-data-seed[oracle]      # oracledb
pip install django-data-seed[dev]         # pytest, pytest-django, ruff, mypy, Pillow, …
pip install django-data-seed[docs]        # mkdocs-material (to build these docs)
```

| Extra | Adds |
|---|---|
| `postgres` | `psycopg[binary]>=3.1` |
| `mysql` | `mysqlclient>=2.1` (MySQL **and** MariaDB) |
| `mssql` | `mssql-django>=1.3` |
| `oracle` | `oracledb>=1.4` |
| `dev` | test + lint toolchain, including `Pillow` for `ImageField` |
| `docs` | `mkdocs-material` for building the documentation site |

!!! tip "ImageField"
    If your models use `ImageField`, install `Pillow` — Django requires it for
    image fields (and the [image provider](features/files.md) uses it to write a
    real 1×1 PNG). It ships in the `dev` extra, or `pip install Pillow`.
