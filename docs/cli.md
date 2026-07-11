# CLI reference — `seeddata`

The management command is a thin wrapper over the [Python API](python-api.md).

```
python manage.py seeddata [targets ...] [options]
```

## Targets

Positional arguments select what to seed. Omit them to seed **every** project
model.

```bash
python manage.py seeddata                 # whole project
python manage.py seeddata shop            # every model in the shop app
python manage.py seeddata shop.Book       # one model
python manage.py seeddata shop.Book blog.Post   # several
```

## Options

| Flag | Default | Description |
|---|---|---|
| `--count N` | `10` | Rows to create **per model**. |
| `--seed N` | — | RNG seed for a byte-for-byte reproducible run. |
| `--locale CODE` | `en` | Locale for realistic data, e.g. `de_DE`, `fr`. |
| `--exclude PATTERN` | — | Glob of labels/apps to skip. Repeatable. |
| `--strategy {reuse,create,mix}` | `reuse` | Foreign-key [strategy](features/relationships.md#foreign-key-strategies). |
| `--mix-ratio F` | `0.2` | For `--strategy mix`, chance of creating a fresh parent. |
| `--realism {smart,uniform}` | `smart` | `smart` = distributions + coherence; `uniform` = dumb-fast noise. |
| `--null-probability F` | `0.1` | Chance a nullable, non-required column is left `NULL`. |
| `--atomic {all,model,none}` | `model` | Transaction scope (see below). |
| `--batch-size N` | `1000` | `bulk_create` batch size. |
| `--using ALIAS` | `default` | Database connection to seed into. |
| `--no-files` | — | Don't write real files for File/Image fields. |
| `--no-preflight` | — | Skip the pre-flight migration/schema checks. |
| `--dry-run` | — | Show the plan and exit **without writing rows**. |
| `--format {text,json}` | `text` | Output format (`json` for CI). |

### `--atomic`

| Value | Meaning |
|---|---|
| `all` | One transaction for the whole run — any model's failure rolls back **everything**. |
| `model` *(default)* | One transaction per model — a failing model is rolled back and skipped, the rest continue, and the command exits non-zero. |
| `none` | No wrapping transaction. |

### `--format json`

Emits a machine-readable summary (and, with `--dry-run`, the plan):

```json
{
  "seed": 42,
  "total": 60,
  "elapsed": 0.31,
  "models": [
    {"label": "shop.Book", "created": 20, "reused_fk": 34, "created_fk": 0, "elapsed": 0.06}
  ]
}
```

## Examples

```bash
# Reproducible whole-project seed
python manage.py seeddata --count 50 --seed 42

# Localised, everything except an audit log
python manage.py seeddata --locale de_DE --exclude '*.AuditLog'

# Load-test-sized table, no file writes
python manage.py seeddata shop.Order --count 100000 --no-files

# Preview the plan only
python manage.py seeddata --dry-run
```

## Deprecated flags

The 0.4.x flags still work for one release, with a warning:

| Old | Use instead |
|---|---|
| `--no-of-objects-to-create`, `--no-of-objects` | `--count` |
| `--django-app` | a positional `app_label` |
| `--django-model` | a positional `app_label.Model` |

See [Migrating](migrating.md).
