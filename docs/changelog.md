# Changelog

The complete, itemised changelog lives in the repository:
**[CHANGELOG.md on GitHub](https://github.com/rohith-baggam/django-data-seed/blob/main/CHANGELOG.md)**.
Highlights below.

## 1.0.0

A ground-up rewrite — see [v0.4 vs v1.0](background/v0-vs-v1.md) for the story
and [Migrating](migrating.md) for the upgrade path.

### Added

- **Mimesis** generation engine (replacing Faker), **field-name inference**, and
  **MRO-based** field dispatch.
- **Constraint decoration** — `max_length`, decimal precision, integer ranges,
  weighted `choices`, IP protocol, `USE_TZ`, configurable NULL injection.
- **Foreign-key dependency graph** with topological ordering, nullable-cycle
  breaking, and clear errors for non-nullable cycles.
- **FK strategies** — `reuse` (default), `create`, `mix`; OneToOne, self-FK
  trees, and M2M handling.
- **Row coherence** — ordered lifecycle dates, one persona/address per row.
- **Single- and multi-column uniqueness**, tracked in memory per target DB.
- **Pre-flight checks** — migrations, schema drift, missing tables, backend
  capabilities.
- **Bulk performance** — `bulk_create` batching, `--atomic all|model|none`.
- **File/Image/FilePath** providers honouring `upload_to`; `--no-files`.
- **Rich CLI** (checklist, plan tree, progress, summary) and `--format json`.
- **Python API** — `seed()`, `SeedPlan`, `SeedResult`.
- **Reproducibility** — `--seed`.
- New flags; **src-layout** packaging with `py.typed`.

### Changed

- App discovery via `apps.get_app_configs()` + `SEED_APPS` / `--exclude`.
- `--no-of-objects-to-create` → `--count` (deprecated alias kept until 1.1).
- Minimum versions raised to Python 3.10 and Django 4.0.

### Removed

- Backup / log-entry / current-user features and their global signal receivers.
- `QueryAuthMiddleware`, the colorama theme, the duplicated `README.rst`.
- The bundled test models that 0.4.x shipped into users' databases.

### Fixed

Every correctness bug from the 0.4.2 audit — URL/Slug dispatch, unique-value
crashes, FK-cycle recursion, double saves, decimal precision, IP protocol — each
with a regression test.
