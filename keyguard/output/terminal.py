from __future__ import annotations
from rich.console import Console
from keyguard.models import Finding

_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "blue",
}


class TerminalReporter:
    def __init__(self, redact: bool = True, console: Console | None = None) -> None:
        self._redact = redact
        self._console = console or Console()

    def report(self, findings: list[Finding]) -> None:
        if not findings:
            self._console.print("[green]No findings detected.[/green]")
            return

        # Print each finding as a structured block
        for f in findings:
            color = _SEVERITY_COLORS.get(f.severity, "white")
            value = "[REDACTED]" if self._redact else f.matched_value
            commit = f.commit or "-"

            self._console.print(f"[{color}][{f.severity.upper()}][/{color}] {f.rule_id}")
            self._console.print(f"  Location: {f.file_path}:{f.line}")
            self._console.print(f"  Value: {value}")
            self._console.print(f"  Commit: {commit}")
            self._console.print()

        self._console.print(
            f"[bold]Found {len(findings)} finding(s).[/bold] "
            f"Critical: {sum(1 for f in findings if f.severity == 'critical')}, "
            f"High: {sum(1 for f in findings if f.severity == 'high')}, "
            f"Medium: {sum(1 for f in findings if f.severity == 'medium')}, "
            f"Low: {sum(1 for f in findings if f.severity == 'low')}."
        )
