from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GcpFinding:
    project_id: str
    project_name: str
    key_id: str
    key_display_name: str
    restriction: str    # "none" | "gemini_explicit"
    severity: str       # "critical" | "high"
    description: str

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "key_id": self.key_id,
            "key_display_name": self.key_display_name,
            "restriction": self.restriction,
            "severity": self.severity,
            "description": self.description,
        }
