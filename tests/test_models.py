from keyguard.models import Chunk, Rule, Finding


def test_chunk_defaults():
    chunk = Chunk(text="hello", file_path="src/app.py", line_offset=1)
    assert chunk.commit is None
    assert chunk.author is None


def test_finding_to_dict_redacts_value():
    finding = Finding(
        rule_id="google-api-key",
        description="Google API Key",
        severity="critical",
        file_path="src/app.py",
        line=10,
        matched_value="AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
        entropy=4.87,
    )
    d = finding.to_dict(redact=True)
    assert d["matched_value"] == "[REDACTED]"
    assert d["rule_id"] == "google-api-key"
    assert d["line"] == 10
    assert d["commit"] is None


def test_finding_to_dict_unredacted():
    finding = Finding(
        rule_id="google-api-key",
        description="Google API Key",
        severity="critical",
        file_path="src/app.py",
        line=10,
        matched_value="AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
        entropy=4.87,
    )
    d = finding.to_dict(redact=False)
    assert d["matched_value"] == "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567"


def test_rule_fields():
    rule = Rule(
        id="google-api-key",
        description="Google API Key",
        pattern=r"AIza[0-9A-Za-z\-_]{35}",
        entropy_min=4.2,
        severity="critical",
        tags=["google", "gemini"],
    )
    assert rule.id == "google-api-key"
    assert rule.tags == ["google", "gemini"]
