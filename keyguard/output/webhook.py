from __future__ import annotations
import json
import sys
import requests
from keyguard.models import Finding


class WebhookNotifier:
    def __init__(self, url: str, format: str = "generic", redact: bool = True) -> None:
        self._url = url
        self._format = format
        self._redact = redact

    def report(self, findings: list[Finding]) -> None:
        if not findings:
            return
        payload = (
            self._build_slack_payload(findings)
            if self._format == "slack"
            else self._build_generic_payload(findings)
        )
        try:
            resp = requests.post(self._url, json=payload, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"Warning: webhook POST failed: {exc}", file=sys.stderr)

    def _build_generic_payload(self, findings: list[Finding]) -> dict:
        return {"findings": [f.to_dict(redact=self._redact) for f in findings]}

    def _build_slack_payload(self, findings: list[Finding]) -> dict:
        lines = [f":warning: *keyguard* detected {len(findings)} finding(s):"]
        for f in findings:
            lines.append(
                f"• `{f.rule_id}` in `{f.file_path}:{f.line}` "
                f"(severity: {f.severity})"
            )
        return {"text": "\n".join(lines)}
