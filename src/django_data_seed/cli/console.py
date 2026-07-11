"""
The rich terminal experience.

Seeding is one of the few dev commands people actually watch run, so the output
is treated as product: a live pre-flight checklist, the dependency graph as a
tree, a progress bar over generation, and a summary table at the finish line.
Everything degrades to plain sequential lines on a non-TTY so CI logs stay
grep-able, and ``--verbosity 0`` stays silent.

The progress bar is started lazily (on the first model, not while printing the
plan) and torn down in ``close()``, which the runner always calls in a
``finally`` -- so a dry run or a mid-run error never leaves the terminal with a
live display still attached.
"""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.tree import Tree

from ..engine.runner import ModelResult, Reporter, SeedResult


class RichReporter(Reporter):
    """Draws the animated pipeline described in the v2 plan's Pillar 7."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.animate = self.console.is_terminal
        self.progress: Progress | None = None
        self.task = None
        self._total = 0

    # -- pre-flight ----------------------------------------------------------

    def preflight(self, results) -> None:
        self.console.print("[bold]Pre-flight[/bold]")
        for check in results:
            if not check.ok:
                mark = "[red]✖[/red]"
            elif getattr(check, "warn", False):
                mark = "[yellow]⚠[/yellow]"
            else:
                mark = "[green]✔[/green]"
            self.console.print(f"  {mark} {check.name}: {check.detail}")

    def unsupported(self, report) -> None:
        if not report:
            return
        self.console.print("[bold]Unsupported fields[/bold] (no generator)")
        for label, fields in report.items():
            for name, required in fields:
                tag = "[red]required[/red]" if required else "[dim]nullable — left NULL[/dim]"
                self.console.print(f"  • {label}.{name} ({tag})")

    # -- the plan ------------------------------------------------------------

    def plan(self, order, count: int) -> None:
        tree = Tree(f"[bold]Seed plan[/bold] — {count} rows per model")
        for model in order.models:
            label = model._meta.label
            broken = order.force_null_fields.get(label)
            suffix = f"  [yellow](nullable cycle broken: {', '.join(sorted(broken))})[/yellow]" \
                if broken else ""
            tree.add(f"{label}{suffix}")
        self.console.print(tree)
        # ? Remember the total; the bar itself starts on the first model so a dry
        # ? run (which returns before any model) never leaves a live display up.
        self._total = len(order.models) * count

    # -- generation ----------------------------------------------------------

    def _ensure_progress(self) -> None:
        if self.progress is None and self.animate and self._total:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
                transient=False,
            )
            self.progress.start()
            self.task = self.progress.add_task("seeding", total=self._total)

    def model_start(self, model, count: int) -> None:
        self._ensure_progress()
        if self.progress is not None and self.task is not None:
            self.progress.update(self.task, description=f"seeding {model._meta.label}")
        elif not self.animate:
            self.console.print(f"  … {model._meta.label} ({count} rows)")

    def tick(self, n: int = 1) -> None:
        if self.progress is not None and self.task is not None:
            self.progress.advance(self.task, n)

    def model_done(self, result: ModelResult) -> None:
        if self.animate:
            return
        if result.skipped:
            self.console.print(f"    [red]✖ {result.label}: skipped — {result.skipped}[/red]")
        else:
            self.console.print(
                f"    [green]✔[/green] {result.label}: {result.created} rows "
                f"({result.elapsed:.2f}s)"
            )

    # -- finish line ---------------------------------------------------------

    def finished(self, result: SeedResult) -> None:
        self.close()

        table = Table(title="Seeded", title_style="bold", show_edge=False)
        table.add_column("Model")
        table.add_column("Rows", justify="right")
        table.add_column("FK reused", justify="right")
        table.add_column("FK created", justify="right")
        table.add_column("Time", justify="right")
        for row in result.per_model:
            if row.skipped:
                table.add_row(
                    f"[red]{row.label}[/red]", "[red]skipped[/red]", "—", "—",
                    f"[red]{row.skipped[:40]}[/red]",
                )
            else:
                table.add_row(
                    row.label,
                    str(row.created),
                    str(row.reused_fk),
                    str(row.created_fk),
                    f"{row.elapsed:.2f}s",
                )
        self.console.print(table)

        seed_note = f" (seed {result.seed})" if result.seed is not None else ""
        skipped = result.skipped
        done_models = len(result.per_model) - len(skipped)
        line = (
            f"[bold green]✨ {result.total} rows across {done_models} "
            f"models in {result.elapsed:.2f}s{seed_note}[/bold green]"
        )
        if skipped:
            line += f"  [red]({len(skipped)} model(s) skipped)[/red]"
        self.console.print(line)

    def close(self) -> None:
        if self.progress is not None:
            self.progress.stop()
            self.progress = None
            self.task = None


def make_reporter(verbosity: int) -> Reporter | None:
    """
    Chooses a reporter for a given management-command verbosity.

    Args:
        - verbosity: Django's ``--verbosity`` (0 silent, 1+ shows the pipeline).

    Returns:
        - A ``RichReporter`` for verbosity >= 1, or ``None`` to stay silent.
    """
    if verbosity <= 0:
        return None
    return RichReporter()
