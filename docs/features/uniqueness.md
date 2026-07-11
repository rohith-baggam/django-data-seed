# Uniqueness

Seeding a table with `unique` columns naively means a database round-trip per
value to check for collisions — an N+1 storm. `django-data-seed` tracks
uniqueness **in memory** instead.

## How it works

For each unique column, the engine loads the existing distinct values **once**,
then generates against that in-memory set with zero further round-trips. UUID
columns skip the check entirely — their collision odds are astronomical.

When a generated value collides, the engine retries; if a column's value space
is tight (say a unique `CharField(max_length=13)`), it folds in seeded entropy so
the run can't dead-end. Because the entropy comes from the seeded RNG, the result
stays reproducible.

## Multi-column uniqueness

`unique_together` and plain `UniqueConstraint(fields=[...])` are tracked too. The
engine builds the whole value-tuple for a row and checks it against the set of
tuples already used before accepting the row, retrying the build until the tuple
is free.

```python
class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(Author, on_delete=models.CASCADE)
    # ...
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["book", "reviewer"], name="one_review"),
        ]
```

Seeding `Review` produces at most one row per `(book, reviewer)` pair.

!!! note "Per target database"
    All uniqueness checks run against the connection you're seeding
    (`--using`), not always `default` — so a multi-database run is correct.

!!! note "Conditional & expression constraints"
    Plain, non-conditional constraints are tracked in memory. Conditional or
    expression constraints are left to the database to enforce.
