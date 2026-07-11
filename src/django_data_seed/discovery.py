"""
Model discovery and selection.

0.4.x discovered "your" apps by walking directory paths under ``BASE_DIR`` --
which breaks under src-layouts and editable installs, and quietly pulled in
sub-app folders. v2 asks Django directly via ``apps.get_app_configs()`` and
excludes the framework/third-party apps by label and by site-packages path,
with ``SEED_APPS`` / ``--exclude`` as the explicit overrides.
"""

from __future__ import annotations

import fnmatch
import os
import site
import sysconfig

from django.apps import apps
from django.conf import settings
from django.db import models

# ? Framework and this package's own app are never seeding targets.
DEFAULT_EXCLUDED_LABELS = {
    "admin",
    "auth",
    "contenttypes",
    "sessions",
    "messages",
    "staticfiles",
    "sites",
    "django_data_seed",
}


def _third_party_roots() -> set[str]:
    """Absolute paths under which installed (non-project) packages live."""
    roots: set[str] = set()
    getter = getattr(site, "getsitepackages", None)
    if getter:
        try:
            roots.update(os.path.abspath(p) for p in getter())
        except Exception:
            pass
    user_site = getattr(site, "getusersitepackages", None)
    if user_site:
        try:
            roots.add(os.path.abspath(user_site()))
        except Exception:
            pass
    for key in ("purelib", "platlib"):
        try:
            roots.add(os.path.abspath(sysconfig.get_paths()[key]))
        except Exception:
            pass
    return roots


def _is_project_app(app_config) -> bool:
    """Whether an app lives in the user's project rather than site-packages."""
    app_path = os.path.abspath(app_config.path)
    return not any(app_path.startswith(root) for root in _third_party_roots())


def _candidate_apps():
    """The app configs eligible for whole-project seeding."""
    configured = getattr(settings, "SEED_APPS", None)
    if configured:
        wanted = set(configured)
        return [
            ac for ac in apps.get_app_configs()
            if ac.label in wanted or ac.name in wanted
        ]
    return [
        ac for ac in apps.get_app_configs()
        if ac.label not in DEFAULT_EXCLUDED_LABELS and _is_project_app(ac)
    ]


def _seedable(model: type[models.Model]) -> bool:
    """Whether a model is a real, directly-seedable table."""
    meta = model._meta
    if meta.abstract or meta.proxy or not meta.managed:
        return False
    if meta.auto_created:
        # ? Auto-created M2M through tables are populated via their M2M field.
        return False
    return True


def _resolve_targets(targets: list[str]) -> list[type[models.Model]]:
    """Resolves ``app_label`` / ``app_label.Model`` strings into model classes."""
    resolved: list[type[models.Model]] = []
    for target in targets:
        if "." in target:
            app_label, model_name = target.split(".", 1)
            resolved.append(apps.get_model(app_label, model_name))
        else:
            app_config = apps.get_app_config(target)
            resolved.extend(m for m in app_config.get_models() if _seedable(m))
    return resolved


def _is_excluded(model: type[models.Model], patterns: list[str]) -> bool:
    label = model._meta.label            # ? "app_label.ModelName"
    app_label = model._meta.app_label
    for pattern in patterns:
        if fnmatch.fnmatch(label, pattern) or fnmatch.fnmatch(app_label, pattern):
            return True
    return False


def select_models(targets=None, exclude=None) -> list[type[models.Model]]:
    """
    Resolves the final list of models to seed.

    Args:
        - targets: Positional selectors (``app_label`` or ``app_label.Model``),
          or ``None`` for the whole project.
        - exclude: Glob patterns of labels/apps to drop.

    Returns:
        - A de-duplicated list of seedable model classes.
    """
    exclude = list(exclude or [])

    if targets:
        found = _resolve_targets(list(targets))
    else:
        found = [
            model
            for app_config in _candidate_apps()
            for model in app_config.get_models()
            if _seedable(model)
        ]

    seen: set[str] = set()
    selected: list[type[models.Model]] = []
    for model in found:
        if not _seedable(model) or _is_excluded(model, exclude):
            continue
        if model._meta.label in seen:
            continue
        seen.add(model._meta.label)
        selected.append(model)
    return selected
