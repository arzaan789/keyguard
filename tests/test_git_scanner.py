import subprocess
from pathlib import Path
from keyguard.scanner.git import GitHistoryScanner
from keyguard.models import Chunk


def _init_repo_with_credential(tmp_path: Path) -> Path:
    """Create a git repo with a committed credential in history."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    secret_file = tmp_path / "config.py"
    secret_file.write_text('API_KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"')
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add config"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    return tmp_path


def test_yields_chunks_from_commits(tmp_path):
    repo_path = _init_repo_with_credential(tmp_path)
    scanner = GitHistoryScanner(repo_path=str(repo_path), exclude=[])
    chunks = list(scanner.scan())
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunks_have_commit_metadata(tmp_path):
    repo_path = _init_repo_with_credential(tmp_path)
    scanner = GitHistoryScanner(repo_path=str(repo_path), exclude=[])
    chunks = list(scanner.scan())
    assert all(c.commit is not None for c in chunks)
    assert all(c.author is not None for c in chunks)


def test_chunk_contains_committed_content(tmp_path):
    repo_path = _init_repo_with_credential(tmp_path)
    scanner = GitHistoryScanner(repo_path=str(repo_path), exclude=[])
    chunks = list(scanner.scan())
    combined = " ".join(c.text for c in chunks)
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X" in combined


def test_graceful_on_non_git_directory(tmp_path, capsys):
    scanner = GitHistoryScanner(repo_path=str(tmp_path), exclude=[])
    chunks = list(scanner.scan())  # must not raise
    assert chunks == []
    captured = capsys.readouterr()
    assert "Warning" in captured.err
