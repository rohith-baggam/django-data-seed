# Row coherence

Faker-style generation produces rows that are individually plausible but mutually
absurd — a `created_at` *after* `updated_at`, a first name that doesn't match the
email, a US city with a German postcode. `django-data-seed` makes each row
**internally consistent** so aggregate data passes the sniff test.

Coherence runs *after* the raw values are generated and *before* foreign keys are
attached, and it never overrides a value you supplied via an override or a unique
column.

## Ordered lifecycle dates

Date and datetime fields on the same row that describe a lifecycle are generated
as an **ordered set**, inferred from their names, with realistic gaps:

```
created_at  ≤  updated_at  ≤  shipped_at  ≤  delivered_at
```

So an order's `delivered_at` is always after its `created_at`, not a random
moment that might predate it.

## One persona per row

Name-like fields on a row are driven by a **single person**, so they agree:

```python
first_name = "Malik"
last_name  = "Bolton"
full_name  = "Malik Bolton"     # not "Priya Nakamura"
```

## One address per row

Location fields (`city`, `state`, `postal_code`, `country`, …) are drawn from a
**single locale record**, so a row's city and postcode belong to the same place
rather than being three unrelated countries stitched together.

## Turning it off

Coherence is part of the `smart` realism layer. Run with `--realism uniform` to
generate every field independently (faster, but incoherent) when you don't care
about how the fields relate.
