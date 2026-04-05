from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    file_path: str
    line_offset: int
    commit: str | None = None
    author: str | None = None


@dataclass
class Rule:
    id: str
    description: str
    pattern: str
    entropy_min: float
    severity: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Finding:
    rule_id: str
    description: str
    severity: str
    file_path: str
    line: int
    matched_value: str
    entropy: float
    commit: str | None = None
    author: str | None = None

    def to_dict(self, redact: bool = True) -> dict:
        value = "[REDACTED]" if redact else self.matched_value
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "file": self.file_path,
            "line": self.line,
            "matched_value": value,
            "entropy": round(self.entropy, 4),
            "commit": self.commit,
            "author": self.author,
        }
