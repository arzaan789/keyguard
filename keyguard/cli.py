from __future__ import annotations
import sys
import click
from keyguard.config import Config, load_config
from keyguard.scan import run_scan
from keyguard.output.terminal import TerminalReporter
from keyguard.output.structured import JsonExporter, SarifExporter
from keyguard.output.webhook import WebhookNotifier


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
