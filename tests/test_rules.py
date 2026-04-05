from keyguard.engine.rules import RuleLoader
from keyguard.models import Rule


def test_loads_builtin_google_rules():
    rules = RuleLoader.load_builtin()
    ids = [r.id for r in rules]
    assert "google-api-key" in ids
    assert "gcp-service-account-key" in ids
    assert "google-oauth-client-secret" in ids


def test_rules_are_rule_instances():
    rules = RuleLoader.load_builtin()
    for rule in rules:
        assert isinstance(rule, Rule)
        assert rule.id
        assert rule.pattern
        assert rule.severity in ("critical", "high", "medium", "low")


def test_merge_custom_rules():
    custom = [
        {
            "id": "my-custom-rule",
            "description": "My custom secret",
            "pattern": r"secret-[a-z0-9]{16}",
            "entropy_min": 3.0,
            "severity": "high",
            "tags": ["custom"],
        }
    ]
    rules = RuleLoader.load_builtin(extra_rules=custom)
    ids = [r.id for r in rules]
    assert "my-custom-rule" in ids
    assert "google-api-key" in ids


def test_disabled_rules_excluded():
    rules = RuleLoader.load_builtin(disabled=["google-api-key"])
    ids = [r.id for r in rules]
    assert "google-api-key" not in ids
    assert "gcp-service-account-key" in ids
