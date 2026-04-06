from unittest.mock import MagicMock, patch
from keyguard.ci.gitlab import GitLabCiScanner
from keyguard.config import CiConfig


def _config(**kwargs) -> CiConfig:
    defaults = dict(gitlab_token="glpat-test", gitlab_url="https://gitlab.com", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data, headers: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
    else:
        r.json.return_value = data
    r.headers = headers or {}
    return r


@patch("keyguard.ci.gitlab.requests.Session")
def test_scans_variables(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"key": "MAPS_KEY", "value": "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"}]),
        _resp(200, []),
    ]
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/api-service"}])
    chunks = list(scanner.scan())
    variable_chunks = [c for c in chunks if c.source_type == "variable"]
    assert len(variable_chunks) == 1
    assert variable_chunks[0].text == "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"
    assert variable_chunks[0].source_id == "MAPS_KEY"


@patch("keyguard.ci.gitlab.requests.Session")
def test_scans_pipeline_job_logs(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, []),
        _resp(200, [{"id": 55}]),
        _resp(200, [{"id": 99}]),
        _resp(200, "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X found in log"),
    ]
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/api-service"}])
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text


@patch("keyguard.ci.gitlab.requests.Session")
def test_403_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _resp(403, {})
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/repo"}])
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err
