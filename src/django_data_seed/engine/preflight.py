"""
Pre-flight checks: never generate a single row against a stale schema.

The most common seeding failure in a real project isn't the value generator --
it's the database being out of step with the models. 0.4.x found out at row
40,000 with an IntegrityError; v2 checks first and stops with a fixable message.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState


@dataclass
class CheckResult:
    """
    One line of the pre-flight checklist.

    Attributes:
        - name: Human label for the check ("Migrations", "Schema", ...).
        - ok: Whether the check passed.
        - detail: A short verdict shown next to the check.
        - fatal: When ``True`` and ``ok`` is ``False``, the run must stop.
        - warn: A non-fatal advisory -- shown as ⚠, never stops the run.
    """

    name: str
    ok: bool
    detail: str
    fatal: bool = False
    warn: bool = False


def check_migrations(connection) -> CheckResult:
    """Reports whether any migrations are unapplied on the connection."""
    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
    except Exception as exc:  # ? A broken migration graph is itself worth surfacing.
        return CheckResult("Migrations", False, f"could not read plan: {exc}", fatal=True)

    if plan:
        pending = ", ".join(
            f"{migration.app_label}.{migration.name}" for migration, _backwards in plan
        )
        return CheckResult(
            "Migrations",
            False,
            f"{len(plan)} unapplied ({pending}) -- run `migrate` first",
            fatal=True,
        )
    return CheckResult("Migrations", True, "all applied")


def check_tables(connection, model_list: list[type[models.Model]]) -> CheckResult:
    """Confirms every managed model selected for seeding actually has a table."""
    existing = set(connection.introspection.table_names())
    missing = []
    for model in model_list:
        meta = model._meta
        if not meta.managed or meta.proxy:
            continue
        if meta.db_table not in existing:
            missing.append(meta.db_table)
    if missing:
        return CheckResult(
            "Schema",
            False,
            f"missing tables: {', '.join(missing)} -- run `migrate`",
            fatal=True,
        )
    return CheckResult("Schema", True, f"{len(model_list)} models in sync")


def check_model_drift(connection, model_list: list[type[models.Model]]) -> CheckResult:
    """
    Detects models changed without a matching migration (the
    ``makemigrations --check`` case). Advisory by default; fatal only when a
    model actually selected for seeding is the one that drifted.

    Args:
        - connection: The database connection (for its migration loader).
        - model_list: The models about to be seeded.

    Returns:
        - A ``CheckResult`` -- ``ok`` when in sync, a ⚠ warn (or fatal) otherwise.
    """
    try:
        executor = MigrationExecutor(connection)
        from_state = executor.loader.project_state()
        to_state = ProjectState.from_apps(_apps())
        autodetector = MigrationAutodetector(from_state, to_state)
        changes = autodetector.changes(graph=executor.loader.graph)
    except Exception as exc:  # ? Never let the drift probe itself break a run.
        return CheckResult("Model drift", True, f"skipped ({exc})")

    if not changes:
        return CheckResult("Model drift", True, "models match migrations")

    changed_apps = set(changes)
    selected_apps = {m._meta.app_label for m in model_list}
    hits = changed_apps & selected_apps
    detail = (
        f"unmigrated changes in {', '.join(sorted(changed_apps))} "
        "-- run `makemigrations`"
    )
    if hits:
        return CheckResult("Model drift", False, detail, fatal=True)
    return CheckResult("Model drift", True, detail, warn=True)


def probe_backend(connection) -> CheckResult:
    """Reports the backend and a couple of capabilities the engine adapts to."""
    features = connection.features
    bits = []
    if getattr(features, "supports_json_field", False):
        bits.append("JSON ✓")
    if getattr(features, "can_return_rows_from_bulk_insert", False):
        bits.append("bulk-returns-pk ✓")
    detail = f"{connection.vendor}" + (f" ({', '.join(bits)})" if bits else "")
    return CheckResult("Database", True, detail)


def run_preflight(connection, model_list: list[type[models.Model]]) -> list[CheckResult]:
    """
    Runs the full pre-flight sequence.

    Args:
        - connection: The database connection to check against.
        - model_list: The models about to be seeded.

    Returns:
        - The ordered list of check results (the caller decides whether a fatal
          failure stops the run).
    """
    return [
        probe_backend(connection),
        check_migrations(connection),
        check_tables(connection, model_list),
        check_model_drift(connection, model_list),
    ]


def _apps():
    """The live app registry (indirection kept for testability)."""
    from django.apps import apps

    return apps
