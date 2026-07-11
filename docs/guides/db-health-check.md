# Guide: check your database health

Every seed run begins with a [pre-flight phase](../features/preflight.md) that
compares your **models** against the **database**. Because `--dry-run` runs that
phase and then stops *without writing anything*, it doubles as a fast schema
health check you can run any time — even in CI.

## The one-liner

```bash
python manage.py seeddata --dry-run
```

```
Pre-flight
  ✔ Database: postgresql (JSON ✓, bulk-returns-pk ✓)
  ✔ Migrations: all applied
  ✔ Schema: 14 models in sync
  ✔ Model drift: models match migrations
Seed plan — 10 rows per model
├── shop.Author
└── shop.Book
```

If something is wrong, it says so and stops:

```
  ✖ Migrations: 2 unapplied (shop.0007_add_isbn, blog.0003_alter_post)
    -- run `migrate` first
```

## What it verifies

- **Unapplied migrations** — the schema is behind your migration files.
- **Missing tables** — a model selected for seeding has no table.
- **Model ↔ migration drift** — you changed a model but haven't run
  `makemigrations`.
- **Backend capabilities** — native UUID/JSON, primary-key return from
  `bulk_create`, datetime precision.

## In CI

Fail the build when the schema and models have drifted, before anything else
runs:

```yaml
# .github/workflows/ci.yml (excerpt)
- name: DB / schema health check
  run: python manage.py seeddata --dry-run
```

Combine with `--format json` if you want to parse the plan programmatically:

```bash
python manage.py seeddata --dry-run --format json
```

## Why this is useful

The most common seeding failure in a real project isn't the generator — it's the
database being out of step with the models. Running this check first turns a
mid-run `IntegrityError` (or a broken deploy) into a clear, up-front message.
