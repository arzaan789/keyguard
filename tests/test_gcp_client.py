from unittest.mock import MagicMock, patch
import pytest
from keyguard.auditor.client import GcpClient, GcpAuthError


def _mock_response(status_code: int, data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_projects_returns_active_only(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {
        "projects": [
            {"projectId": "proj-a", "name": "Active",  "lifecycleState": "ACTIVE"},
            {"projectId": "proj-b", "name": "Deleted", "lifecycleState": "DELETE_REQUESTED"},
        ]
    })
    client = GcpClient()
    projects = client.list_projects()
    assert len(projects) == 1
    assert projects[0]["projectId"] == "proj-a"
    assert projects[0]["name"] == "Active"


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_returns_true(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {"state": "ENABLED"})
    assert GcpClient().gemini_enabled("my-project") is True


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_returns_false_when_disabled(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {"state": "DISABLED"})
    assert GcpClient().gemini_enabled("my-project") is False


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_403_returns_false(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(403, {})
    assert GcpClient().gemini_enabled("my-project") is False


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_keys_returns_keys(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {
        "keys": [{"name": "projects/1/locations/global/keys/abc",
                  "displayName": "My Key", "restrictions": None}]
    })
    keys = GcpClient().list_keys("my-project")
    assert len(keys) == 1
    assert keys[0]["displayName"] == "My Key"


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_keys_403_returns_empty(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(403, {})
    assert GcpClient().list_keys("my-project") == []


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_projects_empty_when_no_projects_key(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {})
    assert GcpClient().list_projects() == []


@patch("keyguard.auditor.client.service_account.Credentials.from_service_account_file")
def test_invalid_credentials_file_raises_auth_error(mock_creds):
    mock_creds.side_effect = FileNotFoundError("not found")
    with pytest.raises(GcpAuthError):
        GcpClient(credentials_file="/nonexistent/key.json")
