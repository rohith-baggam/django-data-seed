# Pre-flight checks

The most common seeding failure in a real project isn't the value generator —
it's the **database being out of step with the models**. `django-data-seed`
checks first and stops with a fixable message, instead of failing halfway through
an insert.

Every run starts with a live checklist:

```
Pre-flight
  ✔ Database: postgresql (JSON ✓, bulk-returns-pk ✓)
  ✔ Migrations: all applied
  ✔ Schema: 14 models in sync
  ✔ Model drift: models match migrations
```

## What it checks

| Check | What it catches |
|---|---|
| **Migrations** | Unapplied migrations — stops and tells you to run `migrate`, rather than failing on a missing column mid-run. |
| **Schema** | A selected model whose table doesn't exist (e.g. a `managed=False` surprise). |
| **Model drift** | Model changes nobody has made a migration for yet (advisory, unless a model being seeded is affected). |
| **Database probe** | The backend's capabilities — native UUID/JSON, whether `bulk_create` returns primary keys, datetime precision — which the engine then adapts to. |

## Using it as a health check

Because `--dry-run` runs the full pre-flight and then stops, it doubles as a
fast **"is my database in sync with my models?"** command — see the
[Check DB health](../guides/db-health-check.md) guide.

```bash
python manage.py seeddata --dry-run
```

## Skipping it

If you know your schema is fine and want to save the check, bypass the pre-flight
phase:

```bash
python manage.py seeddata --no-preflight
```
