from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from keyguard.cli import main
from keyguard.auditor.audit import GcpFinding


def _make_finding(**kwargs) -> GcpFinding:
    defaults = dict(
        project_id="my-project",
        project_name="My Project",
        key_id="abc123",
        key_display_name="Maps Key",
        restriction="none",
        severity="critical",
        description="No restrictions.",
    )
    defaults.update(kwargs)
    return GcpFinding(**defaults)


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_no_findings_exits_zero(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 0


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_with_findings_exits_one(mock_client_cls, mock_audit):
    mock_audit.return_value = [_make_finding()]
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 1


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_output_contains_project_id(mock_client_cls, mock_audit):
    mock_audit.return_value = [_make_finding()]
    result = CliRunner().invoke(main, ["audit"])
    assert "my-project" in result.output


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_specific_project_passed_to_audit(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    CliRunner().invoke(main, ["audit", "--project", "specific-proj"])
    _, kwargs = mock_audit.call_args
    assert kwargs["project_ids"] == ["specific-proj"]


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_no_project_flag_passes_none(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    CliRunner().invoke(main, ["audit"])
    _, kwargs = mock_audit.call_args
    assert kwargs["project_ids"] is None


@patch("keyguard.cli.GcpClient")
def test_audit_auth_error_exits_two(mock_client_cls):
    from keyguard.auditor.client import GcpAuthError
    mock_client_cls.side_effect = GcpAuthError("No credentials")
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 2


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_json_output_writes_file(mock_client_cls, mock_audit, tmp_path):
    mock_audit.return_value = [_make_finding()]
    out = tmp_path / "gcp.json"
    CliRunner().invoke(
        main, ["audit", "--output", "json", "--out-file", str(out)]
    )
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data[0]["project_id"] == "my-project"
