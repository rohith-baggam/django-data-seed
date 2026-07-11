# Demo store

A tiny Django project to try `django-data-seed` against real models.

```bash
cd example_project
pip install -e ..            # install django-data-seed from this repo
python manage.py makemigrations shop
python manage.py migrate
python manage.py seeddata --seed 42
```

Then explore what came out:

```bash
python manage.py seeddata --dry-run          # just the plan
python manage.py seeddata shop.Product --count 100 --strategy reuse
python manage.py shell -c "from shop.models import Order; o=Order.objects.first(); print(o.created_at, o.shipped_at, o.delivered_at)"
```

Things to notice: customer names match their emails, order dates come out in
order, products reuse a small set of categories/suppliers, and the category tree
has real parents — all with no configuration.
