import tempfile
from pathlib import Path
from keyguard.scanner.file import FileScanner
from keyguard.models import Chunk


def test_scans_text_files(tmp_path):
    (tmp_path / "app.py").write_text("print('hello')")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    chunks = list(scanner.scan())
    assert any(c.file_path.endswith("app.py") for c in chunks)


def test_skips_binary_files(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    chunks = list(scanner.scan())
    assert not any(c.file_path.endswith("image.png") for c in chunks)


def test_respects_exclude_patterns(tmp_path):
    (tmp_path / "app.py").write_text("hello")
    (tmp_path / "secret.py").write_text("should be excluded")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=["secret.py"])
    chunks = list(scanner.scan())
    assert not any(c.file_path.endswith("secret.py") for c in chunks)
    assert any(c.file_path.endswith("app.py") for c in chunks)


def test_chunk_line_offset_is_one(tmp_path):
    (tmp_path / "app.py").write_text("line1\nline2\n")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    chunks = list(scanner.scan())
    assert all(c.line_offset == 1 for c in chunks)


def test_chunk_commit_and_author_are_none(tmp_path):
    (tmp_path / "app.py").write_text("hello")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    chunks = list(scanner.scan())
    assert all(c.commit is None for c in chunks)
    assert all(c.author is None for c in chunks)


def test_skips_unreadable_files_without_crash(tmp_path):
    f = tmp_path / "locked.py"
    f.write_text("hello")
    f.chmod(0o000)
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    try:
        chunks = list(scanner.scan())  # must not raise
    finally:
        f.chmod(0o644)  # restore so tmp_path cleanup works


def test_scan_file_returns_single_chunk(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("hello world")
    scanner = FileScanner(paths=[str(tmp_path)], exclude=[])
    chunks = list(scanner.scan_file(str(f)))
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
