# v0.4 vs v1.0

Version 1.0.0 is a **ground-up rewrite**. The concept — zero-config,
whole-project seeding by introspection — is unchanged; almost everything beneath
it is new. This page is the short story of why, and what changed.

## Why a rewrite

`django-data-seed` 0.4.2 worked for the happy path but had correctness problems
in almost every other code path:

- `URLField` and `SlugField` generated plain text (dispatch matched them as
  `CharField`),
- unique numeric fields and the generic unique-retry helper crashed on
  collision,
- foreign-key cycles recursed until the stack blew,
- every seeded object was **saved twice**,
- `DecimalField` ignored `max_digits`,
- the backup/log-entry features registered **unfiltered global signal
  receivers** that ran on every `save()` in the host project — and their
  migrations were gitignored, so those tables never even existed when installed
  from PyPI,
- ~25 test models shipped **inside the package**, creating junk tables in every
  installer's database.

These weren't tweaks to make — they were a design to replace.

## What changed at a glance

| Area | 0.4.x | 1.0.0 |
|---|---|---|
| Generator | Faker | Mimesis ([why](faker-vs-mimesis.md)) |
| Field dispatch | list-order `isinstance` (buggy) | most-specific class by MRO |
| Realistic values | none | field-name inference + locales |
| Foreign keys | fresh parent tree per child (row explosion); cycles crash | dependency graph, reuse-by-default, cycles handled |
| Row coherence | none | ordered dates, one persona/address per row |
| Uniqueness | N+1 `SELECT` per value | in-memory, single **and** multi-column |
| Schema safety | fails mid-insert | pre-flight checks before any write |
| Performance | per-row `create()` (twice!) | `bulk_create`, batched |
| CLI | colorama prints | rich checklist, progress, summary |
| Python API | none | `seed()`, `SeedPlan`, `SeedResult` |
| Reproducibility | none | `--seed` |
| Dependencies | Faker, colorama, … | `Django`, `mimesis`, `rich` |
| Test models | shipped into your DB | live in the package's own test suite |
| Audit/backup/middleware | bundled, global receivers | **removed** (use a dedicated audit package) |

## Breaking changes

1.0 is intentionally breaking. The headline items:

- The **backup / log-entry / current-user** features and their global signal
  receivers are **gone**. Use
  [`django-simple-history`](https://django-simple-history.readthedocs.io/) or
  [`django-auditlog`](https://django-auditlog.readthedocs.io/) for an audit
  trail.
- The bundled **test models** no longer ship.
- `--no-of-objects-to-create` → **`--count`** (old flag warns, removed in 1.1).
- **Python ≥ 3.10** and **Django ≥ 4.0** required.

The full list and upgrade steps are in [Migrating](../migrating.md), and every
change is itemised in the [Changelog](../changelog.md).
