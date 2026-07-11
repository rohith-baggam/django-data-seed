# Python API

Everything the `seeddata` command does is available in code, so seeding fits into
scripts, data migrations, and tests without shelling out.

```python
from django_data_seed import seed, SeedPlan
```

## `seed()`

```python
seed(
    target=None,
    count=10,
    *,
    overrides=None,
    seed=None,
    locale=None,
    strategy="reuse",
    mix_ratio=0.2,
    exclude=None,
    using=None,
    realism="smart",
    null_probability=0.1,
    atomic="model",
    skip_checks=False,
    dry_run=False,
    batch_size=1000,
    reporter=None,
) -> SeedResult
```

**`target`** accepts several shapes:

```python
seed("shop.Book", count=50)          # "app_label.Model" string
seed("shop", count=10)               # a whole app by label
seed(Book, count=50)                 # a model class
seed([Book, Author], count=10)       # a list of the above
seed(count=25)                       # None → every project model
```

The keyword arguments mirror the [CLI flags](cli.md) (`skip_checks` is
`--no-preflight`). It returns a [`SeedResult`](#seedresult).

### Overrides

Generate everything, but pin the fields you care about. An override can be a
value, a callable, a `range`/list (sampled), or a `QuerySet` (used as a foreign-key
reuse pool):

```python
import random

seed(Book, count=50, overrides={
    "title": lambda: random.choice(REAL_TITLES),
    "price": range(5, 100),                          # sampled
    "author": Author.objects.filter(is_active=True), # FK reuse pool
    "status": "published",                           # constant
})
```

For a single target model, `overrides` is a `{field: value}` map. For several
models, key it by label: `{"shop.Book": {"price": ...}}`.

## `SeedPlan`

A small declarative, reusable plan — the programmatic form of a seed script.
Handy for "give every teammate the same demo database":

```python
from django_data_seed import SeedPlan

plan = SeedPlan(defaults={"seed": 42})
plan.add("shop.Author", count=30)
plan.add("shop.Book", count=200, strategy="reuse")
results = plan.run()          # seeds each entry in order
```

`SeedPlan.from_dict({...})` builds a plan from a parsed mapping (e.g. loaded from
your own YAML/JSON):

```python
SeedPlan.from_dict({
    "defaults": {"seed": 42},
    "models": {
        "shop.Author": {"count": 30},
        "shop.Book": {"count": 200},
    },
})
```

## `SeedResult`

Returned by `seed()`; each `SeedPlan` entry returns one too.

| Attribute | Meaning |
|---|---|
| `total` | Total rows created across all models. |
| `per_model` | List of per-model results (`label`, `created`, `reused_fk`, `created_fk`, `elapsed`, `skipped`). |
| `skipped` | The per-model results that failed and were skipped. |
| `seed` | The RNG seed used. |
| `elapsed` | Wall-clock seconds for the run. |
| `dry_run` / `plan` | Set when `dry_run=True`. |

```python
result = seed("shop.Book", count=20, seed=1)
print(result.total)                       # 20
print(result.per_model[0].reused_fk)      # FKs reused for Book
```

## Using it in tests

`seed()` gives you realistic fixtures with one line. Derive the seed from the
test so the data is deterministic and reproduces on failure:

```python
import pytest
from django_data_seed import seed

@pytest.mark.django_db
def test_book_list_view(client):
    seed("shop.Book", count=20, seed=1)   # same 20 books every run
    response = client.get("/books/")
    assert response.status_code == 200
```

See the [Reproducible CI fixtures](guides/reproducible-fixtures.md) guide for
more.
