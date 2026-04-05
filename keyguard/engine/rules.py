from __future__ import annotations
import tomllib
from pathlib import Path
from keyguard.models import Rule

_BUILTIN_RULES_PATH = Path(__file__).parent.parent / "rules" / "google.toml"


class RuleLoader:
    @staticmethod
    def load_builtin(
        extra_rules: list[dict] | None = None,
        disabled: list[str] | None = None,
    ) -> list[Rule]:
        with open(_BUILTIN_RULES_PATH, "rb") as f:
            data = tomllib.load(f)

        all_raw = data.get("rules", [])

        if extra_rules:
            all_raw = all_raw + extra_rules

        disabled_set = set(disabled or [])

        return [
            Rule(
                id=r["id"],
                description=r["description"],
                pattern=r["pattern"],
                entropy_min=float(r.get("entropy_min", 0.0)),
                severity=r["severity"],
                tags=r.get("tags", []),
            )
            for r in all_raw
            if r["id"] not in disabled_set
        ]
