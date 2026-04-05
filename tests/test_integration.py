import subprocess
from pathlib import Path
from keyguard.config import Config
from keyguard.scan import run_scan


def _build_repo(tmp_path: Path) -> Path:
    """Create a git repo with credentials seeded across two commits."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    # Commit 1: add a file with an API key
    (tmp_path / "config.py").write_text(
        'API_KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"\n'
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add config with key"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    # Commit 2: "remove" the key (but it's still in history)
    (tmp_path / "config.py").write_text('API_KEY = "REPLACE_ME"\n')
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "remove key"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    return tmp_path


def test_finds_credential_in_current_files(tmp_path):
    (tmp_path / "app.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"\n'
    )
    config = Config(paths=[str(tmp_path)], scan_git_history=False)
    findings = run_scan(config)
    assert any(f.rule_id == "google-api-key" for f in findings)


def test_current_file_finding_has_no_commit(tmp_path):
    (tmp_path / "app.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"\n'
    )
    config = Config(paths=[str(tmp_path)], scan_git_history=False)
    findings = run_scan(config)
    assert all(f.commit is None for f in findings)


def test_finds_credential_removed_from_current_files(tmp_path):
    """Key deleted from current file must still be found in git history."""
    repo = _build_repo(tmp_path)
    config = Config(paths=[str(repo)], scan_git_history=True)
    findings = run_scan(config)
    history_findings = [f for f in findings if f.commit is not None]
    assert any(f.rule_id == "google-api-key" for f in history_findings)


def test_history_finding_has_commit_and_author(tmp_path):
    repo = _build_repo(tmp_path)
    config = Config(paths=[str(repo)], scan_git_history=True)
    findings = run_scan(config)
    history_findings = [f for f in findings if f.commit is not None]
    assert all(f.author == "test@example.com" for f in history_findings)
    assert all(len(f.commit) == 7 for f in history_findings)


def test_excluded_files_not_scanned(tmp_path):
    (tmp_path / "fixture.py").write_text(
        'KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"\n'
    )
    config = Config(
        paths=[str(tmp_path)],
        exclude=["fixture.py"],
        scan_git_history=False,
    )
    findings = run_scan(config)
    assert findings == []


def test_false_positive_placeholder_not_flagged(tmp_path):
    (tmp_path / "app.py").write_text('KEY = "AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"\n')
    config = Config(paths=[str(tmp_path)], scan_git_history=False)
    findings = run_scan(config)
    assert findings == []
