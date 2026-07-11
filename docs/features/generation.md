# Data generation

Every value goes through the same pipeline: a **type provider** produces
something of the right type, **field-name inference** can override it with
something semantically richer, and **constraint decoration** clamps the result
to the column.

## Field-type providers (MRO dispatch)

Each Django field class has a registered generator. Dispatch walks the field's
**method resolution order** and the most specific registered class wins — so a
`SlugField` (a subclass of `CharField`) resolves to the slug generator, not the
char one. This fixes a whole class of bugs by construction, and means a **custom
field** inherits its parent's generator for free.

Supported field types include:

| Group | Fields |
|---|---|
| Text | `CharField`, `TextField`, `SlugField`, `EmailField`, `URLField` |
| Identity | `UUIDField` |
| Boolean | `BooleanField` (nullable too) |
| Integers | `SmallIntegerField`, `IntegerField`, `BigIntegerField`, and the `Positive*` variants |
| Numbers | `FloatField`, `DecimalField` |
| Temporal | `DateField`, `DateTimeField`, `TimeField`, `DurationField` |
| Network | `GenericIPAddressField` (`IPv4`/`IPv6`/both) |
| Structured | `JSONField`, `BinaryField` |
| Files | `FileField`, `ImageField`, `FilePathField` — see [File & media fields](files.md) |

Django 5's `GeneratedField` is recognised and **skipped** (the database computes
it). `auto_now` / `auto_now_add` columns are left to Django.

## Field-name inference

A value that's the right *type* isn't always the right *thing*. Inference reads
the field's **name** and, when it recognises a common semantic, draws from the
matching provider:

| Column name (examples) | Produces |
|---|---|
| `email`, `email_address` | a real email address |
| `first_name`, `last_name`, `full_name`, `username` | names from one persona |
| `city`, `country`, `state`, `postal_code`, `street` | a coherent address |
| `phone`, `mobile` | a phone number |
| `company`, `job`, `occupation` | company / job title |
| `title`, `description`, `summary`, `bio` | prose of the right length |
| `slug` | a hyphenated slug |
| `price`, `amount`, `salary`, `total` | a realistic amount (log-normal) |
| `latitude`, `longitude` | valid coordinates |
| `age`, `year`, `quantity`, `rating`, `percentage` | sensible numbers |

Inference respects the field type: numeric rules only fire on numeric fields,
text rules only on text fields, and fields with their own strong semantics
(`EmailField`, `URLField`, `SlugField`, …) aren't second-guessed.

!!! example "Why it matters"
    A `CharField(name="city")` becomes `"Rotterdam"` instead of
    `"Lorem ipsum dolor"`. This one feature is what makes a seeded demo
    screenshot look like a real product.

## Constraint decoration

Whatever the provider or inference produced is then made to **fit the column**:

- **`max_length`** — strings truncated at the exact boundary.
- **`max_digits` / `decimal_places`** — decimals quantized to fit.
- **Integer ranges** — respects the field type's storage range and any
  `MinValueValidator` / `MaxValueValidator`.
- **`choices`** — a value is picked from the choices, **weighted** (real status
  columns are 90% `completed`, not a uniform third each), and grouped choices
  are flattened correctly.
- **`GenericIPAddressField` protocol** — `IPv4`, `IPv6`, or a mix, per the field.
- **`USE_TZ`** — datetimes come out timezone-aware or naive to match your project.
- **NULL injection** — nullable, non-required columns are left `NULL` a
  configurable fraction of the time (`--null-probability`, default `0.1`) so your
  optional code paths get exercised. Columns with a `default` are never nulled.

## Realism

By default (`--realism smart`) numbers and dates follow believable shapes rather
than `random.randint`:

- **log-normal** for prices/amounts,
- **weighted** choices for status-like fields,
- **business-hour-weighted** times,
- ordered **lifecycle dates** (see [Row coherence](coherence.md)).

Set `--realism uniform` to turn this off for dumb-fast, uniformly-random values.
