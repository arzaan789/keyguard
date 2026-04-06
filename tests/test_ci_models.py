from keyguard.ci.models import CiChunk, CiFinding


def test_ci_chunk_fields():
    chunk = CiChunk(
        text="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        platform="github",
        repo="my-org/api-service",
        source_type="log",
        source_id="run:123/job:456",
    )
    assert chunk.platform == "github"
    assert chunk.source_type == "log"
    assert chunk.is_name_only is False


def test_ci_chunk_name_only_flag():
    chunk = CiChunk(
        text="GOOGLE_API_KEY",
        platform="circleci",
        repo="my-org/api-service",
        source_type="variable",
        source_id="GOOGLE_API_KEY",
        is_name_only=True,
    )
    assert chunk.is_name_only is True


def test_ci_finding_to_dict_redacts():
    f = CiFinding(
        platform="github",
        repo="my-org/api-service",
        source_type="log",
        source_id="run:123/job:456",
        rule_id="google-api-key",
        severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87,
        line=42,
    )
    d = f.to_dict(redact=True)
    assert d["matched_value"] == "[REDACTED]"
    assert d["platform"] == "github"
    assert d["repo"] == "my-org/api-service"


def test_ci_finding_to_dict_unredacted():
    f = CiFinding(
        platform="github", repo="org/repo", source_type="variable",
        source_id="MAPS_KEY", rule_id="google-api-key", severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87, line=1,
    )
    d = f.to_dict(redact=False)
    assert "AIzaSy" in d["matched_value"]


def test_ci_finding_to_dict_all_keys():
    f = CiFinding(
        platform="github", repo="org/repo", source_type="log",
        source_id="run:1", rule_id="google-api-key", severity="critical",
        matched_value="x", entropy=4.5, line=1,
    )
    assert set(f.to_dict().keys()) == {
        "platform", "repo", "source_type", "source_id",
        "rule_id", "severity", "matched_value", "entropy", "line",
    }
