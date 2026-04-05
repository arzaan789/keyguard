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
