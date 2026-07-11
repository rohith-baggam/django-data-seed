# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [1.0.0] — unreleased

A ground-up rewrite. The concept — zero-config, whole-project seeding by
introspection — is unchanged; almost everything under it is new.

### Added
- **Mimesis generation engine** replacing Faker: faster, typed, locale-aware.
- **Field-name inference** — `email`, `first_name`, `city`, `country`, `price`,
  `latitude`, `slug`, `title`, and more resolve to realistic values by column name.
- **MRO-based field dispatch** — the most specific field class wins by
  construction; custom fields inherit their parent's generator for free.
- **Constraint decoration** — `max_length`, `max_digits`/`decimal_places`,
  integer ranges, `choices` (weighted), `IPv4`/`IPv6` protocol, and configurable
  NULL injection are all honoured.
- **Foreign-key dependency graph** with topological ordering, automatic breaking
  of nullable cycles, and a clear error for non-nullable cycles.
- **FK strategies** — `reuse` (default, fixes the 0.4.x row explosion), `create`,
  and `mix`. OneToOne parents are always fresh; self-FKs stay shallow; M2M links
  attach from the seeded pool.
- **Pre-flight checks** — unapplied migrations, missing tables, and backend
  capabilities are verified before any row is written.
- **Bulk performance** — `bulk_create` batching, in-memory uniqueness (no
  per-value `SELECT`), one transaction per model (`--atomic all|model|none`).
- **Rich CLI** — live pre-flight checklist, dependency-graph tree, progress
  dashboard, and summary table; degrades to plain lines on non-TTY; `--format json`.
- **Public Python API** — `seed(...)`, `SeedPlan`, and `SeedResult`.
- **New flags** — `--count`, `--exclude`, `--seed`, `--locale`, `--strategy`,
  `--realism`, `--null-probability`, `--atomic`, `--batch-size`, `--dry-run`,
  `--format`.
- **src-layout** packaging via a single `pyproject.toml`, with `py.typed`.

### Changed
- App discovery uses `apps.get_app_configs()` with an explicit exclusion list and
  `SEED_APPS` / `--exclude` overrides, instead of walking `BASE_DIR` paths.
- `--no-of-objects-to-create` / `--no-of-objects` → `--count` (old flags kept as
  deprecated aliases that warn; removed in 1.1).
- Minimum versions raised to Python 3.10 and Django 4.0.

### Removed
- The backup / log-entry / current-user features and their **unfiltered global
  signal receivers** — a seeding tool should not hook every `save()` in your
  project. Use `django-simple-history` or `django-auditlog` for an audit trail.
- `QueryAuthMiddleware`, the `sub_app_1` demo app, the colorama theme, and the
  duplicated `README.rst`.
- The ~25 test models that 0.4.x shipped into users' production databases; they
  now live under `tests/testapp/` and never ship.

### Fixed
Regressions fixed with tests (referenced against the 0.4.2 audit):
- URLField/SlugField no longer generate plain text (MRO dispatch).
- Unique numeric / generic-unique helpers no longer crash on collision.
- FK cycles no longer blow the stack.
- Decimals honour `max_digits`; unique text without `max_length` no longer crashes.
- `GenericIPAddressField` respects `protocol`.
- Rows are saved once, not twice.

Fixes from the 1.0.0 pre-release review (each with a regression test):
- Uniqueness is now checked against the **target** database, not always
  `default`, when `--using` selects another connection.
- `--dry-run` no longer leaves the rich progress display running (the reporter
  is always closed); progress is started lazily and torn down in a `finally`.
- A single failing model no longer aborts the run — it is rolled back in its own
  savepoint, recorded as *skipped* in the summary, and the command exits non-zero.
- A typo'd app/model label yields a `CommandError` (with the valid labels), not a
  raw traceback; unsupported-field and cycle errors are wrapped too.
- A QuerySet foreign-key override is resolved **once** per model, not once per row
  (the N+1 is gone).
- Multi-column uniqueness (`unique_together`, `UniqueConstraint`) is tracked.
- Unsupported field types are reported once at plan time — left NULL when
  nullable, fail-fast when required — instead of silently dropped.
- `auto_now` / `auto_now_add` columns are left to Django rather than generated.

### Added (review round)
- File/Image/FilePath field providers (tiny real files; `--no-files` to skip).
- Model↔migration **drift** detection in pre-flight (advisory, fatal only when a
  seeded model is affected).
- **Row coherence**: ordered lifecycle dates, one persona per row, one address
  per row.
- Self-referential FKs form a shallow tree, and broken nullable-cycle edges are
  filled in a post-insert patch pass.
- Nullable foreign keys are sometimes left NULL (exercising optional relations).
- `--strategy create` batches its parent inserts.
- `--no-preflight` (the old `--skip-checks-preflight` stays as a hidden alias);
  `--dry-run --format json` emits the plan; the JSON summary reports skips.
- GitHub Actions CI matrix (Python 3.10–3.14 × Django 4.0→6.0 × SQLite, plus
  PostgreSQL and MySQL service jobs), a `tox.ini`, and a built-wheel smoke test.
- An `example_project/` demo store.

### Fixed (review round 2)
- **Data safety:** the post-insert patch pass (self-FK trees and broken-cycle FK
  wiring) now only ever writes to rows created *during this run* — it no longer
  rewrites pre-existing rows' parents or overwrites deliberate NULL foreign keys.
- `--atomic all` is now genuinely all-or-nothing: the first model failure rolls
  back the whole run and re-raises (per-model isolation stays the behaviour for
  `model`/`none`).
- `--strategy create` recovers its fresh parents' primary keys by identity from
  `bulk_create`, not by slicing an unordered, capped pool (which could hand
  children arbitrary pre-existing rows on PostgreSQL).
- Discarded multi-column-unique retries release the single-column unique values
  they reserved, so a tight unique space isn't burned down over retries.
- File/Image field providers honour the field's string `upload_to` (callables
  fall back to `seed/`), so files land where the app expects them.
- CI installs a valid Mimesis requirement (the matrix rendered the invalid
  `mimesis==>=11`); `Pillow` added to the `dev` extra; the generated
  `example_project` SQLite database is no longer left on disk.
