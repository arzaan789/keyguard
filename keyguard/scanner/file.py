from __future__ import annotations
import sys
from pathlib import Path
from typing import Generator
import pathspec
from keyguard.models import Chunk


class FileScanner:
    def __init__(self, paths: list[str], exclude: list[str]) -> None:
        self._paths = paths
        self._spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude)

    def scan(self) -> Generator[Chunk, None, None]:
        for base in self._paths:
            for path in Path(base).rglob("*"):
                if not path.is_file():
                    continue
                if self._spec.match_file(str(path)):
                    continue
                yield from self.scan_file(str(path))

    def scan_file(self, file_path: str) -> Generator[Chunk, None, None]:
        path = Path(file_path)
        try:
            raw = path.read_bytes()
            if b"\x00" in raw:
                return  # binary file
            text = raw.decode("utf-8", errors="replace")
        except (PermissionError, OSError) as exc:
            print(f"Warning: cannot read {file_path}: {exc}", file=sys.stderr)
            return
        yield Chunk(text=text, file_path=str(path), line_offset=1)
