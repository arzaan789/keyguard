from pathlib import Path
from keyguard.models import Chunk, Rule
from keyguard.engine.matcher import RegexMatcher

FIXTURES = Path(__file__).parent / "fixtures"


def _make_chunk(filename: str) -> Chunk:
    text = (FIXTURES / filename).read_text()
    return Chunk(text=text, file_path=str(FIXTURES / filename), line_offset=1)


def _google_api_key_rule() -> Rule:
    return Rule(
        id="google-api-key",
        description="Google API Key",
        pattern=r"AIza[0-9A-Za-z\-_]{35}",
        entropy_min=4.2,
        severity="critical",
        tags=["google"],
    )


def _service_account_rule() -> Rule:
    return Rule(
        id="gcp-service-account-key",
        description="GCP Service Account RSA private key",
        pattern=r"-----BEGIN RSA PRIVATE KEY-----",
        entropy_min=0.0,
        severity="critical",
        tags=["google", "gcp"],
    )


def test_detects_true_positive_api_key():
    matcher = RegexMatcher([_google_api_key_rule()])
    chunk = _make_chunk("tp_google_api_key.py")
    findings = matcher.scan(chunk)
    assert len(findings) == 1
    assert findings[0].rule_id == "google-api-key"
    assert findings[0].severity == "critical"
    assert findings[0].file_path.endswith("tp_google_api_key.py")


def test_skips_false_positive_low_entropy():
    matcher = RegexMatcher([_google_api_key_rule()])
    chunk = _make_chunk("fp_google_api_key.py")
    findings = matcher.scan(chunk)
    assert findings == []


def test_detects_service_account_key():
    matcher = RegexMatcher([_service_account_rule()])
    chunk = _make_chunk("tp_service_account.json")
    findings = matcher.scan(chunk)
    assert len(findings) == 1
    assert findings[0].rule_id == "gcp-service-account-key"


def test_finding_has_correct_line_number():
    rule = _google_api_key_rule()
    matcher = RegexMatcher([rule])
    text = "line1\nline2\nAPIKEY=AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X\nline4"
    chunk = Chunk(text=text, file_path="config.py", line_offset=1)
    findings = matcher.scan(chunk)
    assert len(findings) == 1
    assert findings[0].line == 3


def test_finding_has_entropy():
    rule = _google_api_key_rule()
    matcher = RegexMatcher([rule])
    chunk = _make_chunk("tp_google_api_key.py")
    findings = matcher.scan(chunk)
    assert findings[0].entropy > 4.2


def test_multiple_rules_applied():
    matcher = RegexMatcher([_google_api_key_rule(), _service_account_rule()])
    text = (FIXTURES / "tp_google_api_key.py").read_text() + "\n" + \
           (FIXTURES / "tp_service_account.json").read_text()
    chunk = Chunk(text=text, file_path="combined.txt", line_offset=1)
    findings = matcher.scan(chunk)
    rule_ids = [f.rule_id for f in findings]
    assert "google-api-key" in rule_ids
    assert "gcp-service-account-key" in rule_ids
