# django-data-seed

**Point it at your Django project and get realistic, constraint-valid data at
bulk-insert speed — with zero configuration.**

```bash
pip install django-data-seed
python manage.py seeddata --count 20 --seed 42
```

<video controls preload="metadata" poster="assets/videos/demo-poster.jpg" style="width:100%;border-radius:8px;margin:1.5rem 0;">
  <source src="assets/videos/demo.mp4" type="video/mp4">
  <track kind="captions" src="assets/videos/demo.vtt" srclang="en" label="English" default>
  Your browser doesn't support embedded video — download it directly:
  <a href="assets/videos/demo.mp4">demo.mp4</a>.
</video>

---

## What is database seeding?

*Seeding* is filling a database with data so you have something to work against —
during development, in a demo, on a staging environment, or inside tests. The
data isn't real, but it should **look** real and **behave** like real data:
valid emails, believable prices, foreign keys that point at rows that exist,
dates that come in a sensible order.

## Why backend developers need it (and how it saves time)

Without a seeding tool, you end up doing one of these, over and over:

- clicking through the Django admin to create a handful of rows by hand,
- writing and maintaining fixture files or a factory per model,
- copying a production dump (and dealing with the privacy headache that brings).

All of it is slow, and the result is usually *junk* — `test test`, `a@a.com`,
every order in the same state — which makes demos look fake and lets bugs hide
until real-shaped data shows up in production.

`django-data-seed` replaces all of that with **one command**. It reads your
models, works out the safe insert order, generates realistic values, and
bulk-inserts them — turning "an afternoon of fixtures" into a few seconds.

## What is django-data-seed?

A Django app that seeds your whole project (or a single model) by
**introspection**. You don't describe your data — it figures your schema out and
generates data that fits it:

- realistic values from [Mimesis](https://mimesis.name/), refined by the field's
  **name** (`city` → a city) and **constraints** (`max_length`, `choices`, …);
- foreign keys resolved through a **dependency graph** so parents exist before
  children, reusing rows instead of exploding a fresh tree per child;
- rows that are internally **coherent** (ordered dates, one persona per row);
- `bulk_create` speed, in-memory uniqueness, and a **pre-flight check** that
  refuses to run against a stale schema.

## Why django-data-seed (vs the alternatives)

| | factory_boy | model_bakery | django-seed | **django-data-seed** |
|---|---|---|---|---|
| Setup per model | write a Factory | none (junk values) | none | **none** |
| Realistic values | only if you write them | no | Faker, no inference | **inference + locales** |
| Whole-project seeding | no | no | yes (unmaintained) | **yes** |
| Bulk performance | no | no | no | **`bulk_create`, batched** |
| Maintained in 2026 | yes | yes | **no** | **yes** |

`factory_boy` and `model_bakery` are great *inside unit tests* — but they make
you write a factory per model. `django-seed` did whole-project seeding but is
unmaintained. `django-data-seed` fills that gap: zero-config, realistic,
whole-project, fast — and maintained.

## Where to next

- **[Getting started](getting-started.md)** — install, configure, first seed.
- **[Features](features/index.md)** — everything the engine does, explained.
- **[CLI reference](cli.md)** and **[Python API](python-api.md)**.
- **[Guides](guides/demo-data.md)** — practical recipes.
- **[Faker vs Mimesis](background/faker-vs-mimesis.md)** and
  **[v0.4 vs v1.0](background/v0-vs-v1.md)** — the "why" behind the rewrite.
