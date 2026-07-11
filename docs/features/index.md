# Features overview

`django-data-seed` is a pipeline: it works out **what** to generate, makes each
value **fit the column**, wires up **relationships** correctly, keeps each row
**coherent**, and inserts everything **fast** — after checking your schema is
sound.

<div class="grid cards" markdown>

- :material-shape:{ .lg } **[Data generation](generation.md)**

    Every field type produces a valid value. Values are refined by the field's
    name (`city` → a city) and clamped to its constraints (`max_length`,
    `choices`, decimal precision, integer ranges, IP protocol).

- :material-graph:{ .lg } **[Relationships](relationships.md)**

    A foreign-key dependency graph seeds parents before children, reuses rows
    instead of exploding trees, and handles OneToOne, self-FKs, M2M, and cycles.

- :material-link-variant:{ .lg } **[Row coherence](coherence.md)**

    Fields within a row agree: ordered lifecycle dates, one persona per name
    set, one address per city/state/zip.

- :material-fingerprint:{ .lg } **[Uniqueness](uniqueness.md)**

    Single- and multi-column uniqueness tracked in memory — no per-value
    `SELECT`, no collisions.

- :material-airplane-check:{ .lg } **[Pre-flight checks](preflight.md)**

    Unapplied migrations, schema drift, and missing tables are caught before any
    row is written.

- :material-file:{ .lg } **[File & media fields](files.md)**

    File/Image/FilePath fields get real, tiny files under your `MEDIA_ROOT`,
    honouring each field's `upload_to`.

</div>

## The generation pipeline

For every field, the engine resolves a value in this order — first match wins:

1. **User override** — an explicit value/callable/pool you supplied.
2. **NULL injection** — for nullable, non-required columns (configurable).
3. **Weighted choice** — for `choices` fields (skewed, not uniform).
4. **Field-name inference** — `email`, `city`, `price`, `latitude`, …
5. **Field-type provider** — dispatched by the field's real MRO.

Whatever comes out is then **decorated** to fit the column (length, numeric
range, decimal shape) and, for unique columns, checked against an in-memory set.

## Performance & reproducibility

- `bulk_create` in batches; one transaction per model (`--atomic all|model|none`).
- Uniqueness handled in memory — zero per-value round-trips.
- `--seed N` makes the entire run **byte-for-byte reproducible**.
- Realism has an off switch: `--realism uniform` for dumb-fast noise.
