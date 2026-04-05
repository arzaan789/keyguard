from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    paths: list[str] = field(default_factory=lambda: ["."])
    exclude: list[str] = field(default_factory=list)
    scan_git_history: bool = True
    output_formats: list[str] = field(default_factory=lambda: ["terminal"])
    out_file: str | None = None
    redact: bool = True
    slack_webhook: str | None = None
    webhook_url: str | None = None
    disabled_rules: list[str] = field(default_factory=list)
    extra_rules: list[dict] = field(default_factory=list)


def load_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = Path(".keyguard.toml")

    if not config_path.exists():
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid .keyguard.toml: {exc}") from exc

    scan = data.get("scan", {})
    output = data.get("output", {})
    notify = data.get("notify", {})
    rules = data.get("rules", {})

    return Config(
        paths=scan.get("paths", ["."]),
        exclude=scan.get("exclude", []),
        scan_git_history=scan.get("scan_git_history", True),
        output_formats=output.get("format", ["terminal"]),
        redact=output.get("redact", True),
        slack_webhook=notify.get("slack_webhook"),
        webhook_url=notify.get("webhook_url"),
        disabled_rules=rules.get("disabled", []),
        extra_rules=rules.get("extra", []),
    )
