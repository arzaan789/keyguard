from unittest.mock import patch
from click.testing import CliRunner
from keyguard.cli import main
from keyguard.ci.models import CiFinding


def _finding(**kwargs) -> CiFinding:
    defaults = dict(
        platform="github", repo="org/repo", source_type="log",
        source_id="run:1", rule_id="google-api-key", severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87, line=1,
    )
    defaults.update(kwargs)
    return CiFinding(**defaults)


def _toml_with_ci(tmp_path) -> str:
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[ci]\ngithub_token = "ghp_test"\n')
    return str(toml)


@patch("keyguard.cli.ci_scan")
def test_ci_no_findings_exits_zero(mock_scan, tmp_path):
    mock_scan.return_value = []
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert result.exit_code == 0


@patch("keyguard.cli.ci_scan")
def test_ci_with_findings_exits_one(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert result.exit_code == 1


@patch("keyguard.cli.ci_scan")
def test_ci_output_contains_platform(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert "github" in result.output.lower()


def test_ci_no_tokens_exits_two(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[scan]\npaths = ["."]\n')
    result = CliRunner().invoke(main, ["ci", "--config", str(toml)])
    assert result.exit_code == 2


@patch("keyguard.cli.ci_scan")
def test_ci_platform_flag_passed(mock_scan, tmp_path):
    mock_scan.return_value = []
    CliRunner().invoke(main, ["ci", "--platform", "github", "--config", _toml_with_ci(tmp_path)])
    _, kwargs = mock_scan.call_args
    assert kwargs["platform"] == "github"


@patch("keyguard.cli.ci_scan")
def test_ci_json_output_writes_file(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    out = tmp_path / "ci.json"
    CliRunner().invoke(
        main, ["ci", "--output", "json", "--out-file", str(out), "--config", _toml_with_ci(tmp_path)]
    )
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data[0]["platform"] == "github"
