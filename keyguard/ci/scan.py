from __future__ import annotations
from keyguard.ci.models import CiChunk, CiFinding
from keyguard.ci.github import GitHubCiScanner
from keyguard.ci.circleci import CircleCiScanner
from keyguard.ci.gitlab import GitLabCiScanner
from keyguard.config import CiConfig
from keyguard.engine.rules import RuleLoader
from keyguard.engine.matcher import RegexMatcher
from keyguard.models import Chunk


def ci_scan(
    ci_config: CiConfig,
    platform: str | None = None,
    repos: list[str] | None = None,
) -> list[CiFinding]:
    rules = RuleLoader.load_builtin(disabled=[], extra_rules=[])
    matcher = RegexMatcher(rules)
    findings: list[CiFinding] = []

    scanners = []
    if (platform is None or platform == "github") and ci_config.github_token:
        scanners.append(GitHubCiScanner(ci_config, repos_override=repos))
    if (platform is None or platform == "circleci") and ci_config.circleci_token:
        scanners.append(CircleCiScanner(ci_config, repos_override=repos))
    if (platform is None or platform == "gitlab") and ci_config.gitlab_token:
        scanners.append(GitLabCiScanner(ci_config, repos_override=repos))

    for scanner in scanners:
        for ci_chunk in scanner.scan():
            if ci_chunk.is_name_only:
                findings.append(CiFinding(
                    platform=ci_chunk.platform,
                    repo=ci_chunk.repo,
                    source_type="variable",
                    source_id=ci_chunk.source_id,
                    rule_id="masked-variable-name",
                    severity="info",
                    matched_value=f"[masked: {ci_chunk.text}]",
                    entropy=0.0,
                    line=0,
                ))
            else:
                chunk = Chunk(
                    text=ci_chunk.text,
                    file_path=ci_chunk.source_id,
                    line_offset=1,
                )
                for finding in matcher.scan(chunk):
                    findings.append(CiFinding(
                        platform=ci_chunk.platform,
                        repo=ci_chunk.repo,
                        source_type=ci_chunk.source_type,
                        source_id=ci_chunk.source_id,
                        rule_id=finding.rule_id,
                        severity=finding.severity,
                        matched_value=finding.matched_value,
                        entropy=finding.entropy,
                        line=finding.line,
                    ))

    return findings
