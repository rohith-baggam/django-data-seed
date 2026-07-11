"""
The ``seeddata`` management command -- a thin wrapper over ``django_data_seed.seed``.

    manage.py seeddata                      # every project model, 10 rows each
    manage.py seeddata shop.Book --count 50
    manage.py seeddata shop --exclude shop.AuditLog --seed 42
    manage.py seeddata --dry-run            # show the plan, write nothing

The 0.4.x flags (``--no-of-objects-to-create``, ``--django-app``,
``--django-model``) are kept as hidden, deprecated aliases for one release so
existing scripts keep working while printing a nudge toward the new flags.
"""

from __future__ import annotations

import argparse
import json

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from ...api import seed
from ...cli.console import make_reporter
from ...engine.graph import HardCycleError
from ...engine.runner import PreflightFailed, SeedResult, UnsupportedFieldError


class Command(BaseCommand):
    help = "Populate the database with realistic, constraint-valid seed data."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "targets",
            nargs="*",
            help="Models to seed as app_label or app_label.Model. Omit to seed "
            "every project model.",
        )
        parser.add_argument("--count", type=int, default=10,
                            help="Rows to create per model (default: 10).")
        parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                            help="Glob of labels/apps to skip (repeatable).")
        parser.add_argument("--seed", type=int, default=None,
                            help="RNG seed for a reproducible run.")
        parser.add_argument("--locale", type=str, default=None,
                            help="Locale for realistic data, e.g. de_DE.")
        parser.add_argument("--strategy", choices=["reuse", "create", "mix"], default="reuse",
                            help="Foreign-key strategy (default: reuse).")
        parser.add_argument("--mix-ratio", type=float, default=0.2,
                            help="For --strategy mix, chance of creating a fresh parent.")
        parser.add_argument("--realism", choices=["smart", "uniform"], default="smart",
                            help="'smart' distributions/temporal shapes, or 'uniform'.")
        parser.add_argument("--null-probability", type=float, default=0.1,
                            help="Chance a nullable, non-required column is left NULL.")
        parser.add_argument("--atomic", choices=["all", "model", "none"], default="model",
                            help="Transaction scope (default: model).")
        parser.add_argument("--batch-size", type=int, default=1000,
                            help="bulk_create batch size (default: 1000).")
        parser.add_argument("--using", type=str, default=None,
                            help="Database alias to seed into.")
        parser.add_argument("--no-files", dest="make_files", action="store_false",
                            help="Skip writing real files for File/Image fields.")
        parser.add_argument("--no-preflight", dest="skip_preflight",
                            action="store_true",
                            help="Bypass the pre-flight migration/schema checks.")
        # ? Hidden alias for the old, awkwardly-named flag.
        parser.add_argument("--skip-checks-preflight", dest="skip_preflight",
                            action="store_true", help=argparse.SUPPRESS)
        parser.add_argument("--dry-run", action="store_true",
                            help="Show the plan and exit without writing rows.")
        parser.add_argument("--format", choices=["text", "json"], default="text",
                            help="Output format (default: text).")

        # * Deprecated 0.4.x aliases -- hidden, mapped onto the new flags.
        parser.add_argument("--no-of-objects-to-create", type=int, dest="legacy_count",
                            default=None, help=argparse.SUPPRESS)
        parser.add_argument("--no-of-objects", type=int, dest="legacy_count2",
                            default=None, help=argparse.SUPPRESS)
        parser.add_argument("--django-app", type=str, dest="legacy_app",
                            default=None, help=argparse.SUPPRESS)
        parser.add_argument("--django-model", type=str, dest="legacy_model",
                            default=None, help=argparse.SUPPRESS)

    def handle(self, *args, **options) -> None:
        targets = list(options["targets"])
        count = options["count"]

        # ? Fold the deprecated aliases in, warning once for each that's used.
        legacy_count = options.get("legacy_count") or options.get("legacy_count2")
        if legacy_count is not None:
            self._warn_deprecated("--no-of-objects[-to-create]", "--count")
            count = legacy_count
        if options.get("legacy_app"):
            self._warn_deprecated("--django-app", "a positional app_label")
            targets.append(options["legacy_app"])
        if options.get("legacy_model"):
            self._warn_deprecated("--django-model", "a positional app_label.Model")
            targets.append(options["legacy_model"])

        verbosity = 0 if options["format"] == "json" else options["verbosity"]
        reporter = make_reporter(verbosity)

        try:
            result = seed(
                target=targets or None,
                count=count,
                seed=options["seed"],
                locale=options["locale"],
                strategy=options["strategy"],
                mix_ratio=options["mix_ratio"],
                exclude=options["exclude"],
                using=options["using"],
                realism=options["realism"],
                null_probability=options["null_probability"],
                atomic=options["atomic"],
                skip_checks=options["skip_preflight"],
                dry_run=options["dry_run"],
                make_files=options["make_files"],
                batch_size=options["batch_size"],
                reporter=reporter,
            )
        except (PreflightFailed, HardCycleError, UnsupportedFieldError) as exc:
            raise CommandError(str(exc)) from exc
        except LookupError as exc:
            # ? A typo'd app/model label -- point the user at the valid ones.
            raise CommandError(f"{exc}\n\nAvailable models: {self._available_labels()}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["format"] == "json":
            payload = _plan_as_dict(result) if result.dry_run else _result_as_dict(result)
            self.stdout.write(json.dumps(payload, indent=2))

        # ? A partially-skipped run is a failure -- exit non-zero for CI.
        if result.skipped:
            raise CommandError(
                f"{len(result.skipped)} model(s) were skipped due to errors: "
                + ", ".join(r.label for r in result.skipped)
            )

    def _available_labels(self) -> str:
        labels = sorted(m._meta.label for m in apps.get_models())
        return ", ".join(labels)

    def _warn_deprecated(self, old: str, new: str) -> None:
        self.stderr.write(
            self.style.WARNING(
                f"{old} is deprecated and will be removed in 1.1; use {new}."
            )
        )


def _result_as_dict(result: SeedResult) -> dict:
    """Serialises a run result for ``--format json`` (CI-friendly)."""
    return {
        "seed": result.seed,
        "total": result.total,
        "elapsed": round(result.elapsed, 4),
        "skipped": [r.label for r in result.skipped],
        "models": [
            {
                "label": row.label,
                "created": row.created,
                "reused_fk": row.reused_fk,
                "created_fk": row.created_fk,
                "elapsed": round(row.elapsed, 4),
                "skipped": row.skipped,
            }
            for row in result.per_model
        ],
    }


def _plan_as_dict(result: SeedResult) -> dict:
    """Serialises the dry-run plan for ``--dry-run --format json``."""
    return {"seed": result.seed, "dry_run": True, "plan": result.plan}
