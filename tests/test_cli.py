from keyguard.scan import run_scan
from keyguard.config import Config


def test_run_scan_returns_list(tmp_path):
    (tmp_path / "clean.py").write_text("print('hello')")
    config = Config(paths=[str(tmp_path)], scan_git_history=False)
    findings = run_scan(config)
    assert isinstance(findings, list)
    assert findings == []


def test_run_scan_finds_credential(tmp_path):
    (tmp_path / "config.py").write_text(
        'API_KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"'
    )
    config = Config(paths=[str(tmp_path)], scan_git_history=False)
    findings = run_scan(config)
    assert len(findings) == 1
    assert findings[0].rule_id == "google-api-key"


from click.testing import CliRunner
from keyguard.cli import main


def test_scan_clean_directory_exits_zero(tmp_path):
    (tmp_path / "app.py").write_text("print('hello')")
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--no-git-history"])
    assert result.exit_code == 0


def test_scan_with_credential_exits_one(tmp_path):
    (tmp_path / "config.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"'
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--no-git-history"])
    assert result.exit_code == 1


def test_scan_outputs_rule_id(tmp_path):
    (tmp_path / "config.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"'
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--no-git-history"])
    assert "google-api-key" in result.output


def test_scan_json_output_writes_file(tmp_path):
    (tmp_path / "config.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"'
    )
    out = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["scan", str(tmp_path), "--no-git-history", "--output", "json", "--out-file", str(out)],
    )
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert len(data) == 1


def test_watch_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["watch", "--help"])
    assert result.exit_code == 0
    assert "watch" in result.output or "Watch" in result.output
