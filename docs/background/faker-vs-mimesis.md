# Faker vs Mimesis

`django-data-seed` 0.4.x generated values with [Faker](https://faker.readthedocs.io/).
The 1.0 rewrite moved to [Mimesis](https://mimesis.name/). Here's why.

## Why the switch

| | Faker | **Mimesis** |
|---|---|---|
| Per-value speed | slow (heavy per-call overhead) | ~10–60× faster |
| Typing | untyped | fully typed |
| Locales | yes | first-class, structured providers |
| API shape | flat `fake.x()` | organised providers (`person`, `address`, `finance`, …) |

Seeding is a **bulk** operation — you generate hundreds of thousands of values in
a run — so per-value overhead dominates. Faker's per-call cost is the main reason
0.4.x seeding felt slow even before its N+1 queries. Mimesis generates the same
kinds of values far faster, which is exactly what a bulk seeder needs.

## Realism isn't a library feature

An important point the rewrite is built around: **no fake-data library ships
realism as a whole.** Faker and Mimesis both give you individually-plausible
values — but a row where `created_at` is after `updated_at`, or a US city with a
German postcode, is still absurd.

Realism lives in the **relationships between values**, and that layer is ours:

- [constraint decoration](../features/generation.md#constraint-decoration) makes
  each value legal for its column,
- [row coherence](../features/coherence.md) makes the values within a row agree,
- distributions (log-normal prices, weighted statuses) make aggregates believable.

Mimesis supplies fast, locale-aware primitives; `django-data-seed` builds the
intelligence on top. Swapping the primitive engine for a faster one made that
layer cheaper to run — but the layer is the point.

## What this means for you

- Faker and `colorama` are **no longer dependencies**.
- Runtime deps are just `Django`, `mimesis`, and `rich`
  (see [Dependencies](../dependencies.md)).
- Values are generated much faster, and localisation is a first-class `--locale`
  flag.
