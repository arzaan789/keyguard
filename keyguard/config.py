from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CiConfig:
    github_token: str | None = None
    circleci_token: str | None = None
    gitlab_token: str | None = None
    gitlab_url: str = "https://gitlab.com"
    max_runs: int = 10
    github_orgs: list[str] = field(default_factory=list)
    github_repos: list[str] = field(default_factory=list)
    circleci_orgs: list[str] = field(default_factory=list)
    gitlab_groups: list[str] = field(default_factory=list)
    gitlab_repos: list[str] = field(default_factory=list)


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
    ci: CiConfig | None = None


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
    ci_raw = data.get("ci", {})

    ci_config: CiConfig | None = None
    if ci_raw:
        ci_config = CiConfig(
            github_token=ci_raw.get("github_token"),
            circleci_token=ci_raw.get("circleci_token"),
            gitlab_token=ci_raw.get("gitlab_token"),
            gitlab_url=ci_raw.get("gitlab_url", "https://gitlab.com"),
            max_runs=int(ci_raw.get("max_runs", 10)),
            github_orgs=ci_raw.get("github", {}).get("orgs", []),
            github_repos=ci_raw.get("github", {}).get("repos", []),
            circleci_orgs=ci_raw.get("circleci", {}).get("orgs", []),
            gitlab_groups=ci_raw.get("gitlab", {}).get("groups", []),
            gitlab_repos=ci_raw.get("gitlab", {}).get("repos", []),
        )

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
        ci=ci_config,
    )
