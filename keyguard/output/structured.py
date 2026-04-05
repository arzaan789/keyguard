from __future__ import annotations
import json
from keyguard.models import Finding

_SARIF_SEVERITY = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


class JsonExporter:
    def __init__(self, out_file: str, redact: bool = True) -> None:
        self._out_file = out_file
        self._redact = redact

    def report(self, findings: list[Finding]) -> None:
        data = [f.to_dict(redact=self._redact) for f in findings]
        with open(self._out_file, "w") as fh:
            json.dump(data, fh, indent=2)


class SarifExporter:
    def __init__(self, out_file: str, redact: bool = True) -> None:
        self._out_file = out_file
        self._redact = redact

    def report(self, findings: list[Finding]) -> None:
        rule_ids = list({f.rule_id for f in findings})
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "keyguard",
                            "version": "0.1.0",
                            "rules": [{"id": rid} for rid in rule_ids],
                        }
                    },
                    "results": [self._finding_to_result(f) for f in findings],
                }
            ],
        }
        with open(self._out_file, "w") as fh:
            json.dump(sarif, fh, indent=2)

    def _finding_to_result(self, finding: Finding) -> dict:
        value = "[REDACTED]" if self._redact else finding.matched_value
        return {
            "ruleId": finding.rule_id,
            "level": _SARIF_SEVERITY.get(finding.severity, "warning"),
            "message": {"text": f"{finding.description}: {value}"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file_path},
                        "region": {"startLine": finding.line},
                    }
                }
            ],
        }
