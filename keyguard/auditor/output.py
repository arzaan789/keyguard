from __future__ import annotations
import json
from rich.console import Console
from rich.table import Table
from rich import box
from keyguard.auditor.audit import GcpFinding

_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
}


class GcpTerminalReporter:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def report(self, findings: list[GcpFinding]) -> None:
        if not findings:
            self._console.print("[green]No GCP findings detected.[/green]")
            return

        by_project: dict[str, list[GcpFinding]] = {}
        for f in findings:
            by_project.setdefault(f.project_id, []).append(f)

        for project_id, pfindings in by_project.items():
            pname = pfindings[0].project_name
            self._console.print(f"\nProject: {pname} ({project_id})")
            self._console.print("  Gemini API: ENABLED")

            table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
            table.add_column("Severity")
            table.add_column("Restriction")
            table.add_column("Key")
            table.add_column("Description")

            for f in pfindings:
                color = _SEVERITY_COLORS.get(f.severity, "white")
                table.add_row(
                    f"[{color}]{f.severity.upper()}[/{color}]",
                    f.restriction,
                    f.key_display_name,
                    f.description,
                )
            self._console.print(table)

        critical = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        self._console.print(
            f"Found {len(findings)} finding(s). "
            f"Critical: {critical}, High: {high}."
        )


class GcpJsonExporter:
    def __init__(self, out_file: str) -> None:
        self._out_file = out_file

    def report(self, findings: list[GcpFinding]) -> None:
        with open(self._out_file, "w") as fh:
            json.dump([f.to_dict() for f in findings], fh, indent=2)
