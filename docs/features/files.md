# File & media fields

`FileField`, `ImageField`, and `FilePathField` are handled by writing **real,
tiny files** so the stored path actually points at something.

## What gets written

| Field | Behaviour |
|---|---|
| `FileField` | A small text file is written and its name stored. |
| `ImageField` | A real 1×1 PNG is written (needs `Pillow`) and its name stored. |
| `FilePathField` | A path is chosen from the configured directory if it has files, otherwise synthesised. |

Files are written under your project's **`MEDIA_ROOT`**, into the directory the
field declares via **`upload_to`**:

```python
class Book(models.Model):
    cover = models.ImageField(upload_to="covers/")   # → MEDIA_ROOT/covers/<name>.png
    sample = models.FileField(upload_to="samples/")  # → MEDIA_ROOT/samples/<name>.txt
```

A string `upload_to` is honoured so files land where your application expects
them. A callable `upload_to` (which needs a real instance and filename that don't
exist yet at generation time) falls back to a `seed/` prefix — still under
`MEDIA_ROOT`.

## Skipping file writes

If you don't want files touched on disk — for example when seeding a very large
table, or in CI where `MEDIA_ROOT` is throwaway — use `--no-files`. A name is
still stored on the column, but nothing is written:

```bash
python manage.py seeddata --no-files
```

!!! tip "Pillow"
    `ImageField` requires [Pillow](https://pillow.readthedocs.io/)
    (`pip install Pillow`, or the `dev` extra). Without it, Django's own system
    check for `ImageField` fails regardless of this package.
