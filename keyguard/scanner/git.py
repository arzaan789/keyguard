from __future__ import annotations
import sys
from typing import Generator
import git
from keyguard.models import Chunk


class GitHistoryScanner:
    def __init__(self, repo_path: str, exclude: list[str]) -> None:
        self._repo_path = repo_path
        self._exclude = set(exclude)

    def scan(self) -> Generator[Chunk, None, None]:
        try:
            repo = git.Repo(self._repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            print(
                f"Warning: {self._repo_path} is not a git repository, skipping history scan",
                file=sys.stderr,
            )
            return

        for commit in repo.iter_commits():
            parent = commit.parents[0] if commit.parents else None
            if parent is None:
                # Initial commit: scan all blobs in the tree
                for blob in commit.tree.traverse():
                    if blob.type != "blob":
                        continue
                    yield from self._blob_to_chunk(blob, blob.path, commit)
            else:
                diffs = commit.diff(parent)
                for diff in diffs:
                    if diff.b_blob is None:
                        continue
                    yield from self._blob_to_chunk(diff.b_blob, diff.b_path, commit)

    def _blob_to_chunk(self, blob, file_path: str, commit) -> Generator[Chunk, None, None]:
        if any(exc in file_path for exc in self._exclude):
            return
        try:
            raw = blob.data_stream.read()
            if b"\x00" in raw:
                return
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return
        yield Chunk(
            text=text,
            file_path=file_path,
            line_offset=1,
            commit=commit.hexsha[:7],
            author=commit.author.email,
        )
