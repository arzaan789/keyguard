from __future__ import annotations
import sys
import click
from keyguard.config import Config, load_config
from keyguard.scan import run_scan
from keyguard.output.terminal import TerminalReporter
from keyguard.output.structured import JsonExporter, SarifExporter
from keyguard.output.webhook import WebhookNotifier
from keyguard.auditor.client import GcpClient, GcpAuthError
from keyguard.auditor.audit import audit_projects
from keyguard.auditor.output import GcpTerminalReporter, GcpJsonExporter


@click.group()
def main() -> None:
    """keyguard — scan codebases for exposed credentials."""


@main.command()
@click.argument("path", default=".")
@click.option("--output", "output_formats", multiple=True,
              type=click.Choice(["terminal", "json", "sarif"]),
              help="Output format (repeatable). Defaults to terminal.")
@click.option("--out-file", default=None, help="Base path for structured output files.")
@click.option("--no-git-history", is_flag=True, default=False,
              help="Skip scanning git commit history.")
@click.option("--no-redact", is_flag=True, default=False,
              help="Show full matched values (not redacted).")
@click.option("--config", "config_path", default=".keyguard.toml",
              help="Path to .keyguard.toml config file.")
def scan(path, output_formats, out_file, no_git_history, no_redact, config_path) -> None:
    """Scan PATH for exposed credentials."""
    try:
        config = load_config(config_path=config_path if config_path != ".keyguard.toml" else None)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    # CLI flags override config
    config.paths = [path]
    if output_formats:
        config.output_formats = list(output_formats)
    if out_file:
        config.out_file = out_file
    if no_git_history:
        config.scan_git_history = False
    if no_redact:
        config.redact = False

    findings = run_scan(config)
    redact = config.redact

    if "terminal" in config.output_formats or not config.output_formats:
        TerminalReporter(redact=redact).report(findings)

    if "json" in config.output_formats and config.out_file:
        out = config.out_file if config.out_file.endswith(".json") else config.out_file + ".json"
        JsonExporter(out_file=out, redact=redact).report(findings)

    if "sarif" in config.output_formats and config.out_file:
        out = config.out_file if config.out_file.endswith(".sarif") else config.out_file + ".sarif"
        SarifExporter(out_file=out, redact=redact).report(findings)

    if config.slack_webhook:
        WebhookNotifier(url=config.slack_webhook, format="slack", redact=redact).report(findings)
    elif config.webhook_url:
        WebhookNotifier(url=config.webhook_url, format="generic", redact=redact).report(findings)

    sys.exit(1 if findings else 0)


@main.command()
@click.argument("path", default=".")
@click.option("--no-redact", is_flag=True, default=False)
@click.option("--config", "config_path", default=".keyguard.toml")
def watch(path, no_redact, config_path) -> None:
    """Watch PATH and re-scan on file changes."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    from keyguard.engine.rules import RuleLoader
    from keyguard.engine.matcher import RegexMatcher
    from keyguard.scanner.file import FileScanner

    try:
        config = load_config(config_path=config_path if config_path != ".keyguard.toml" else None)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    config.paths = [path]
    if no_redact:
        config.redact = False

    rules = RuleLoader.load_builtin(
        extra_rules=config.extra_rules, disabled=config.disabled_rules
    )
    matcher = RegexMatcher(rules)
    reporter = TerminalReporter(redact=config.redact)

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            scanner = FileScanner(paths=[path], exclude=config.exclude)
            findings = []
            for chunk in scanner.scan_file(event.src_path):
                findings.extend(matcher.scan(chunk))
            if findings:
                reporter.report(findings)

    observer = Observer()
    observer.schedule(_Handler(), path=path, recursive=True)
    observer.start()
    click.echo(f"Watching {path} for changes. Press Ctrl+C to stop.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@main.group()
def rules() -> None:
    """Manage detection rules."""


@rules.command("list")
@click.option("--config", "config_path", default=".keyguard.toml")
def rules_list(config_path) -> None:
    """List all active detection rules."""
    from keyguard.engine.rules import RuleLoader

    try:
        config = load_config(config_path=config_path if config_path != ".keyguard.toml" else None)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    loaded_rules = RuleLoader.load_builtin(
        extra_rules=config.extra_rules, disabled=config.disabled_rules
    )
    click.echo(f"{'ID':<35} {'SEVERITY':<10} {'DESCRIPTION'}")
    click.echo("-" * 80)
    for r in loaded_rules:
        click.echo(f"{r.id:<35} {r.severity:<10} {r.description}")
    click.echo(f"\n{len(loaded_rules)} rule(s) active.")


@main.group()
def config() -> None:
    """Manage keyguard configuration."""


@config.command("check")
@click.option("--config", "config_path", default=".keyguard.toml")
def config_check(config_path) -> None:
    """Validate a .keyguard.toml configuration file."""
    from pathlib import Path

    try:
        cfg = load_config(config_path=Path(config_path))
        click.echo(f"Config is valid. Paths: {cfg.paths}, Rules disabled: {cfg.disabled_rules}")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


@main.command()
@click.option(
    "--project", "project_ids", multiple=True,
    help="GCP project ID to audit (repeatable). Default: auto-discover all.",
)
@click.option(
    "--gcp-credentials", default=None,
    help="Path to service account JSON key. Default: Application Default Credentials.",
)
@click.option(
    "--output", "output_formats", multiple=True,
    type=click.Choice(["json"]),
    help="Additional output format. Terminal is always on.",
)
@click.option("--out-file", default=None, help="Path for JSON output file.")
def audit(project_ids, gcp_credentials, output_formats, out_file) -> None:
    """Audit GCP projects for API keys with Gemini access."""
    try:
        client = GcpClient(credentials_file=gcp_credentials or None)
    except GcpAuthError as exc:
        click.echo(
            f"Error: {exc}\n"
            "Run `gcloud auth application-default login` "
            "or pass `--gcp-credentials key.json`",
            err=True,
        )
        sys.exit(2)

    project_list = list(project_ids) if project_ids else None
    findings = audit_projects(client, project_ids=project_list)

    GcpTerminalReporter().report(findings)

    if "json" in output_formats and out_file:
        GcpJsonExporter(out_file=out_file).report(findings)

    sys.exit(1 if findings else 0)
