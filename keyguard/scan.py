from __future__ import annotations
from keyguard.config import Config
from keyguard.engine.rules import RuleLoader
from keyguard.engine.matcher import RegexMatcher
from keyguard.models import Finding
from keyguard.scanner.file import FileScanner
from keyguard.scanner.git import GitHistoryScanner


def run_scan(config: Config) -> list[Finding]:
    rules = RuleLoader.load_builtin(
        extra_rules=config.extra_rules,
        disabled=config.disabled_rules,
    )
    matcher = RegexMatcher(rules)
    findings: list[Finding] = []

    file_scanner = FileScanner(paths=config.paths, exclude=config.exclude)
    for chunk in file_scanner.scan():
        findings.extend(matcher.scan(chunk))

    if config.scan_git_history:
        for path in config.paths:
            git_scanner = GitHistoryScanner(repo_path=path, exclude=config.exclude)
            for chunk in git_scanner.scan():
                findings.extend(matcher.scan(chunk))

    return findings
