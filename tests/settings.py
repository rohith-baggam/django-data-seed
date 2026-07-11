"""Minimal Django settings for the test suite.

Defaults to in-memory SQLite. CI points the ``default`` connection at
PostgreSQL/MySQL via ``DDS_DB_*`` environment variables so the same suite runs
across every supported backend. The ``secondary`` alias stays SQLite so the
multi-database uniqueness test (A1) always has a distinct connection.
"""

import os
import tempfile

SECRET_KEY = "django-data-seed-test-key-not-secret"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_data_seed",
    "tests.testapp",
]


def _default_database() -> dict:
    engine = os.environ.get("DDS_DB_ENGINE", "django.db.backends.sqlite3")
    if "sqlite" in engine:
        return {"ENGINE": engine, "NAME": ":memory:"}
    return {
        "ENGINE": engine,
        "NAME": os.environ.get("DDS_DB_NAME", "django_data_seed"),
        "USER": os.environ.get("DDS_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DDS_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DDS_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DDS_DB_PORT", ""),
    }


DATABASES = {
    "default": _default_database(),
    # ? A second alias so the multi-database uniqueness fix (A1) can be tested.
    "secondary": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"

# ? Seeded File/Image fields write tiny real files under here.
MEDIA_ROOT = tempfile.mkdtemp(prefix="dds-test-media-")

# ? Keep the test project quiet and dependency-free.
LOGGING_CONFIG = None
