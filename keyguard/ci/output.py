from __future__ import annotations
import json
from rich.console import Console
from rich.table import Table
from rich import box
from keyguard.ci.models import CiFinding

_SEVERITY_COLORS = {"critical": "bold red", "high": "red", "info": "blue"}


class CiTerminalReporter:
    def __init__(self, console: Console | None = None, redact: bool = True) -> None:
        self._console = console or Console()
        self._redact = redact

    def report(self, findings: list[CiFinding]) -> None:
        if not findings:
            self._console.print("[green]No CI findings detected.[/green]")
            return

        by_platform: dict[str, list[CiFinding]] = {}
        for f in findings:
            by_platform.setdefault(f.platform, []).append(f)

        for platform, pfindings in by_platform.items():
            self._console.print(f"\nPlatform: {platform}")
            by_repo: dict[str, list[CiFinding]] = {}
            for f in pfindings:
                by_repo.setdefault(f.repo, []).append(f)

            for repo, rfindings in by_repo.items():
                self._console.print(f"  Repo: {repo}")
                table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                table.add_column("Severity")
                table.add_column("Type")
                table.add_column("Rule")
                table.add_column("Source")
                table.add_column("Value")

                for f in rfindings:
                    color = _SEVERITY_COLORS.get(f.severity, "white")
                    value = "[REDACTED]" if self._redact else f.matched_value
                    table.add_row(
                        f"[{color}]{f.severity.upper()}[/{color}]",
                        f.source_type,
                        f.rule_id,
                        f.source_id,
                        value,
                    )
                self._console.print(table)

        critical = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        info = sum(1 for f in findings if f.severity == "info")
        self._console.print(
            f"Found {len(findings)} finding(s). "
            f"Critical: {critical}, High: {high}, Info: {info}."
        )


class CiJsonExporter:
    def __init__(self, out_file: str, redact: bool = True) -> None:
        self._out_file = out_file
        self._redact = redact

    def report(self, findings: list[CiFinding]) -> None:
        with open(self._out_file, "w") as fh:
            json.dump([f.to_dict(redact=self._redact) for f in findings], fh, indent=2)
