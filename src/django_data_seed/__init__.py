"""
django-data-seed
================

Zero-config, whole-project database seeding for Django.

Point it at your project (or a single model) and get realistic,
constraint-valid data at bulk-insert speed -- no per-model factories to write::

    from django_data_seed import seed

    seed("shop.Book", count=50)              # one model
    seed(count=25)                           # every project model
    seed(Book, count=50, overrides={         # override only what you care about
        "title": lambda: "Hand-picked title",
    })

Everything the ``seeddata`` management command does is available here.
"""

from __future__ import annotations

__version__ = "1.0.1"

__all__ = [
    "seed",
    "SeedPlan",
    "SeedResult",
    "SeedConfig",
    "FKStrategy",
    "__version__",
]


def __getattr__(name: str):
    # ? Lazy imports so ``import django_data_seed`` doesn't require the Django
    # ? app registry to be ready (e.g. when read for its ``__version__`` alone).
    if name in {"seed", "SeedPlan"}:
        from . import api

        return getattr(api, name)
    if name in {"SeedResult", "SeedConfig"}:
        from .engine import runner

        return getattr(runner, name)
    if name == "FKStrategy":
        from .engine.relations import FKStrategy

        return FKStrategy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
