from unittest.mock import MagicMock, patch
from keyguard.ci.github import GitHubCiScanner
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig


def _config(**kwargs) -> CiConfig:
    defaults = dict(github_token="ghp_test", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
    else:
        r.json.return_value = data
    r.headers = {}
    return r


@patch("keyguard.ci.github.requests.Session")
def test_scans_variables(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, {"variables": [
            {"name": "MAPS_KEY", "value": "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"},
        ]}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_repos=["my-org/api-service"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    variable_chunks = [c for c in chunks if c.source_type == "variable"]
    assert len(variable_chunks) == 1
    assert variable_chunks[0].text == "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"
    assert variable_chunks[0].platform == "github"
    assert variable_chunks[0].repo == "my-org/api-service"
    assert variable_chunks[0].source_id == "MAPS_KEY"


@patch("keyguard.ci.github.requests.Session")
def test_scans_job_logs(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, {"variables": []}),
        _resp(200, {"workflow_runs": [{"id": 111}]}),
        _resp(200, {"jobs": [{"id": 999}]}),
        _resp(200, "log line with AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X here"),
    ]
    cfg = _config(github_repos=["my-org/api-service"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text
    assert log_chunks[0].source_id == "run:111/job:999"


@patch("keyguard.ci.github.requests.Session")
def test_403_on_variables_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(403, {}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_repos=["my-org/private-repo"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err


@patch("keyguard.ci.github.requests.Session")
def test_org_repos_listed(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"full_name": "my-org/repo-a"}]),
        _resp(200, {"variables": []}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_orgs=["my-org"])
    scanner = GitHubCiScanner(cfg)
    list(scanner.scan())
    assert session.get.call_count >= 2
