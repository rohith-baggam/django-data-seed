# Migrating from 0.4.x to 1.0

1.0.0 is a rewrite. It is a **breaking** release — read this before upgrading.

## Breaking changes

### 1. Backup / log-entry / current-user features removed
The `DjangoSeedDataBackUpModel`, `DjangoSeedDataLogEntryModel`, the global
`pre_save`/`post_delete` receivers, `CurrentUserMiddleware`, and the thread-local
user tracking are **gone**. In 0.4.x these registered receivers with no
`sender=` filter, so they ran on every `save()` in your project — and their
migrations were gitignored, so the tables never even existed when installed from
PyPI.

If you need an audit trail, use a package built for it:
[`django-simple-history`](https://django-simple-history.readthedocs.io/) or
[`django-auditlog`](https://django-auditlog.readthedocs.io/). Remove any
`DJANGO_SEED_*` backup/log settings and drop `CurrentUserMiddleware` from
`MIDDLEWARE`.

### 2. Test models no longer ship
0.4.x defined ~25 `DjangoDataSeed*` models inside the installed package, so
`migrate` created ~25 junk tables in your database (four also registered in the
admin). These are gone. After upgrading, you can create a migration to drop the
leftover tables from your project.

### 3. `--no-of-objects-to-create` → `--count`
```bash
# old
python manage.py seeddata --no-of-objects-to-create 50 --django-app shop
# new
python manage.py seeddata shop --count 50
```
The old flags (`--no-of-objects-to-create`, `--no-of-objects`, `--django-app`,
`--django-model`) still work but print a deprecation warning. They are removed in
1.1.

### 4. Targets are positional
Apps and models are now positional arguments: `seeddata shop`,
`seeddata shop.Book`. Pass several at once, and use `--exclude` to skip.

### 5. Version floors raised
Python ≥ 3.10 and Django ≥ 4.0 are required.

## What you gain

Realistic values via field-name inference, correct foreign-key ordering with
FK reuse (no more row explosion), pre-flight migration/schema checks, `bulk_create`
speed, reproducible runs with `--seed`, a `--dry-run` plan, JSON output for CI,
and a public `seed()` / `SeedPlan` Python API. See the [README](README.md) and
[CHANGELOG](CHANGELOG.md).
