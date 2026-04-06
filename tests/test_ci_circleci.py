import re
from unittest.mock import MagicMock, patch
from keyguard.ci.circleci import CircleCiScanner
from keyguard.config import CiConfig

_SUSPICIOUS = re.compile(r"(GOOGLE|GEMINI|GCP|FIREBASE|GCLOUD|VERTEX)", re.IGNORECASE)


def _config(**kwargs) -> CiConfig:
    defaults = dict(circleci_token="CCIPAT_test", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
        r.json.side_effect = ValueError("Not JSON")
    else:
        r.json.return_value = data
    return r


@patch("keyguard.ci.circleci.requests.Session")
def test_suspicious_variable_name_yields_name_only_chunk(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"name": "GOOGLE_API_KEY", "value": "xxxxxx"},
                    {"name": "DB_HOST", "value": "xxxxxx"}]),
        _resp(200, {"items": []}),
    ]
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    name_chunks = [c for c in chunks if c.is_name_only]
    assert len(name_chunks) == 1
    assert name_chunks[0].text == "GOOGLE_API_KEY"
    assert name_chunks[0].source_id == "GOOGLE_API_KEY"


@patch("keyguard.ci.circleci.requests.Session")
def test_non_suspicious_variable_not_yielded(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"name": "DB_HOST", "value": "xxxxxx"}]),
        _resp(200, {"items": []}),
    ]
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    assert not any(c.is_name_only for c in chunks)


@patch("keyguard.ci.circleci.requests.Session")
def test_log_scanning_yields_log_chunk(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, []),
        _resp(200, {"items": [{"id": "pipe-1", "number": 42}]}),
        _resp(200, {"items": [{"id": "wf-1"}]}),
        _resp(200, {"items": [{"id": 99, "job_number": 42}]}),
        _resp(200, "step output: AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"),
    ]
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text


@patch("keyguard.ci.circleci.requests.Session")
def test_401_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _resp(401, {})
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err
