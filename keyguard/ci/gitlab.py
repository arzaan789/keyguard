from __future__ import annotations
import sys
from typing import Generator
import requests
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig


class GitLabCiScanner:
    def __init__(
        self,
        config: CiConfig,
        repos_override: list[dict] | None = None,
    ) -> None:
        self._config = config
        self._repos_override = repos_override
        self._base = config.gitlab_url.rstrip("/") + "/api/v4"
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {config.gitlab_token}"})

    def scan(self) -> Generator[CiChunk, None, None]:
        for project in self._resolve_projects():
            pid = project["id"]
            path = project["path_with_namespace"]
            yield from self._scan_variables(pid, path)
            yield from self._scan_logs(pid, path)

    def _resolve_projects(self) -> list[dict]:
        if self._repos_override:
            return self._repos_override
        projects: list[dict] = []
        for group in self._config.gitlab_groups:
            projects.extend(self._list_group_projects(group))
        for repo in self._config.gitlab_repos:
            projects.append({"id": repo, "path_with_namespace": repo})
        return projects

    def _list_group_projects(self, group: str) -> list[dict]:
        resp = self._get(f"{self._base}/groups/{group}/projects?per_page=100")
        if resp is None:
            return []
        return [{"id": p["id"], "path_with_namespace": p["path_with_namespace"]}
                for p in resp.json()]

    def _scan_variables(self, project_id: int, path: str) -> Generator[CiChunk, None, None]:
        resp = self._get(f"{self._base}/projects/{project_id}/variables")
        if resp is None:
            return
        for var in resp.json():
            yield CiChunk(
                text=var.get("value", ""),
                platform="gitlab",
                repo=path,
                source_type="variable",
                source_id=var["key"],
            )

    def _scan_logs(self, project_id: int, path: str) -> Generator[CiChunk, None, None]:
        resp = self._get(
            f"{self._base}/projects/{project_id}/pipelines"
            f"?per_page={self._config.max_runs}"
        )
        if resp is None:
            return
        for pipeline in resp.json():
            jobs_resp = self._get(
                f"{self._base}/projects/{project_id}/pipelines/{pipeline['id']}/jobs"
            )
            if jobs_resp is None:
                continue
            for job in jobs_resp.json():
                log_resp = self._get(
                    f"{self._base}/projects/{project_id}/jobs/{job['id']}/trace"
                )
                if log_resp and log_resp.status_code == 200:
                    yield CiChunk(
                        text=log_resp.text[:1_000_000],
                        platform="gitlab",
                        repo=path,
                        source_type="log",
                        source_id=f"pipeline:{pipeline['id']}/job:{job['id']}",
                    )

    def _get(self, url: str) -> requests.Response | None:
        try:
            resp = self._session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (401, 403, 404):
                print(f"Warning: HTTP {resp.status_code} for {url}", file=sys.stderr)
            return None
        except requests.RequestException as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            return None
