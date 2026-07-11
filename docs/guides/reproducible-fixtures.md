# Guide: reproducible CI fixtures

`seed()` gives you realistic test data in one line. The key to using it in tests
is the **`seed=` argument** — it makes the generated data deterministic, so a
test behaves the same on your laptop and in CI, and a failure reproduces exactly.

## pytest

```python
import pytest
from django_data_seed import seed
from shop.models import Book

@pytest.mark.django_db
def test_book_list_shows_all_books(client):
    seed("shop.Book", count=20, seed=1)
    response = client.get("/books/")
    assert response.status_code == 200
    assert Book.objects.count() == 20
```

A neat pattern is to derive the seed from the test's name so every test gets its
own stable dataset:

```python
def _seed_for(request):
    return abs(hash(request.node.nodeid)) % (2**31)

@pytest.mark.django_db
def test_something(request):
    seed("shop.Order", count=50, seed=_seed_for(request))
    ...
```

## Django `TestCase`

Seed once per test class in `setUpTestData` (fast — one insert, wrapped in a
transaction that's rolled back per test):

```python
from django.test import TestCase
from django_data_seed import seed

class BookViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed("shop.Book", count=20, seed=1)

    def test_list(self):
        self.assertEqual(self.client.get("/books/").status_code, 200)
```

## Load-shaped data

Because the same call scales, "does this view survive a real table size?" becomes
a five-line test instead of a staging exercise:

```python
@pytest.mark.django_db
def test_book_list_at_scale(client, django_assert_max_num_queries):
    seed("shop.Book", count=100_000, seed=1, atomic="model")
    with django_assert_max_num_queries(5):
        client.get("/books/")
```

## Tips

- Pass `--realism uniform` / `realism="uniform"` if you want the fastest possible
  generation and don't need coherent, distribution-shaped data.
- Keep `skip_checks=False` (the default) in CI so a fixture run also catches an
  unmigrated schema.
