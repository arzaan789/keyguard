from __future__ import annotations
import re
from keyguard.models import Chunk, Rule, Finding
from keyguard.entropy import calculate_entropy


class RegexMatcher:
    def __init__(self, rules: list[Rule]) -> None:
        self._rules = rules
        self._compiled = {rule.id: re.compile(rule.pattern) for rule in rules}

    def scan(self, chunk: Chunk) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self._rules:
            pattern = self._compiled[rule.id]
            for match in pattern.finditer(chunk.text):
                matched = match.group(0)
                entropy = calculate_entropy(matched)
                if entropy < rule.entropy_min:
                    continue
                line_in_chunk = chunk.text[: match.start()].count("\n") + 1
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        description=rule.description,
                        severity=rule.severity,
                        file_path=chunk.file_path,
                        line=chunk.line_offset + line_in_chunk - 1,
                        matched_value=matched,
                        entropy=entropy,
                        commit=chunk.commit,
                        author=chunk.author,
                    )
                )
        return findings
