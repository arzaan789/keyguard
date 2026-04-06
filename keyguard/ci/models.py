from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CiChunk:
    text: str
    platform: str       # "github" | "circleci" | "gitlab"
    repo: str           # "owner/name"
    source_type: str    # "log" | "variable"
    source_id: str      # run/job ID for logs; variable name for variables
    is_name_only: bool = False  # True for CircleCI masked variable name checks


@dataclass
class CiFinding:
    platform: str
    repo: str
    source_type: str    # "log" | "variable"
    source_id: str
    rule_id: str
    severity: str       # "critical" | "high" | "info"
    matched_value: str
    entropy: float
    line: int

    def to_dict(self, redact: bool = True) -> dict:
        value = "[REDACTED]" if redact else self.matched_value
        return {
            "platform": self.platform,
            "repo": self.repo,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "matched_value": value,
            "entropy": round(self.entropy, 4),
            "line": self.line,
        }
