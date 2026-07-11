# Guide: seed a demo store

Goal: a populated database you can click through in the admin or show in a demo,
generated the same way every time.

## 1. Seed the whole project

```bash
python manage.py seeddata --count 20 --seed 42
```

`--seed 42` means you (and your teammates) get the **identical** dataset every
run. Parents are seeded before children automatically, and foreign keys reuse
those parents, so you get realistic cardinality rather than one author per book.

## 2. Tune the amounts per model

Some tables want more rows than others. Seed them individually, largest parents
first:

```bash
python manage.py seeddata shop.Author --count 30 --seed 42
python manage.py seeddata shop.Category --count 12 --seed 42
python manage.py seeddata shop.Book --count 300 --seed 42   # reuses authors & categories
```

Or capture it as a reusable [`SeedPlan`](../python-api.md#seedplan) so it's one
command for everyone:

```python
# scripts/seed_demo.py
from django_data_seed import SeedPlan

plan = SeedPlan(defaults={"seed": 42})
plan.add("shop.Author", count=30)
plan.add("shop.Category", count=12)
plan.add("shop.Book", count=300)
plan.run()
```

```bash
python manage.py shell -c "import scripts.seed_demo"
```

## 3. Browse it

```bash
python manage.py createsuperuser
python manage.py runserver
# open http://127.0.0.1:8000/admin/
```

## 4. Reset when you want fresh data

```bash
# start over
rm -f db.sqlite3 && python manage.py migrate
python manage.py seeddata --count 20 --seed 42
```

## Tips

- Use `--locale de_DE` (or another locale) to demo a localised store.
- Use `--dry-run` first to eyeball the seed order and row counts.
- `--strategy mix` gives more natural parent/child spread than pure reuse.
