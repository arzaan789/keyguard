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


def audit_projects(
    client: "GcpClient",  # type: ignore[name-defined]
    project_ids: list[str] | None = None,
) -> list[GcpFinding]:
    if project_ids is None:
        projects = client.list_projects()
    else:
        projects = [{"projectId": pid, "name": pid} for pid in project_ids]

    findings: list[GcpFinding] = []

    for project in projects:
        pid = project["projectId"]
        pname = project["name"]

        if not client.gemini_enabled(pid):
            continue

        for key in client.list_keys(pid):
            key_name = key.get("name", "")
            key_id = key_name.rsplit("/", 1)[-1] if key_name else "unknown"
            key_display = key.get("displayName", key_id)
            restrictions = key.get("restrictions") or {}
            api_targets = restrictions.get("apiTargets", [])

            if not api_targets:
                findings.append(GcpFinding(
                    project_id=pid,
                    project_name=pname,
                    key_id=key_id,
                    key_display_name=key_display,
                    restriction="none",
                    severity="critical",
                    description=(
                        f"Key '{key_display}' has no API restrictions and Gemini is enabled "
                        f"on project '{pid}' — any API including Gemini is accessible."
                    ),
                ))
            else:
                gemini_targets = [
                    t for t in api_targets
                    if t.get("service") == "generativelanguage.googleapis.com"
                ]
                if gemini_targets:
                    findings.append(GcpFinding(
                        project_id=pid,
                        project_name=pname,
                        key_id=key_id,
                        key_display_name=key_display,
                        restriction="gemini_explicit",
                        severity="high",
                        description=(
                            f"Key '{key_display}' explicitly allows "
                            f"generativelanguage.googleapis.com on project '{pid}'."
                        ),
                    ))

    return findings
