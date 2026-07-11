# Relationships

Getting relationships right is where naive seeders fall over — they either
insert children before parents (integrity errors) or create a brand-new parent
tree for every child (row explosion). `django-data-seed` builds the foreign-key
graph up front and seeds in the correct order.

## Dependency graph & insert order

The engine builds a graph of foreign keys across the selected models,
topologically sorts it, and seeds **parents before children**. You can see the
order any time with `--dry-run`:

```
Seed plan — 10 rows per model
├── shop.Author
├── shop.Publisher
├── shop.Tag
└── shop.Book        # ← seeded last; its FKs already exist
```

## Foreign-key strategies

How a foreign key is filled is controlled by `--strategy` (or the `strategy=`
argument in Python):

| Strategy | Behaviour |
|---|---|
| `reuse` *(default)* | Point at an **existing** row of the target. Creates a parent only if the table is empty. Fixes the row-explosion problem. |
| `create` | Create a fresh parent per child (the old behaviour), batched. |
| `mix` | Mostly reuse, occasionally create — for realistic cardinality. Tune with `--mix-ratio`. |

With `reuse`, "hot" parents are picked more often than cold ones (a Zipf-like
bias), which is what real cardinality looks like — a few authors write most of
the books.

## OneToOne, self-FK, and M2M

- **OneToOneField** always gets its **own** fresh parent — sharing one would
  violate the uniqueness of the relation.
- **Self-referential FK** (category trees, org charts) forms a **shallow tree**:
  a fraction of rows are roots, the rest point at earlier rows. Only rows created
  in this run are wired — existing rows are never touched.
- **ManyToManyField** with an auto-created through table gets a small random
  sample (0–5) of existing targets attached to each row. An **explicit through
  model** is seeded as an ordinary model in graph order.

## Cycles

Foreign-key cycles are handled deliberately, not by crashing:

- A cycle that runs through a **nullable** FK is **broken**: the edge is seeded
  `NULL` first, then filled in a post-insert patch pass (again, only on rows this
  run created).
- A cycle made entirely of **non-nullable** FKs cannot be ordered — the engine
  stops and prints the offending cycle path, so you can make one key nullable or
  exclude a model.

## Skipped models

Abstract, proxy, and unmanaged models, and auto-created M2M through tables, are
skipped automatically (the last are populated via their M2M field, not directly).
