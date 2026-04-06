from __future__ import annotations
import sys
from typing import Generator
import requests
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig

_BASE = "https://api.github.com"


class GitHubCiScanner:
    def __init__(self, config: CiConfig, repos_override: list[str] | None = None) -> None:
        self._config = config
        self._repos_override = repos_override
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {config.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def scan(self) -> Generator[CiChunk, None, None]:
        for repo in self._resolve_repos():
            yield from self._scan_variables(repo)
            yield from self._scan_logs(repo)

    def _resolve_repos(self) -> list[str]:
        if self._repos_override:
            return self._repos_override
        repos: list[str] = list(self._config.github_repos)
        for org in self._config.github_orgs:
            repos.extend(self._list_org_repos(org))
        return list(dict.fromkeys(repos))

    def _list_org_repos(self, org: str) -> list[str]:
        repos: list[str] = []
        url: str | None = f"{_BASE}/orgs/{org}/repos?per_page=100"
        while url:
            resp = self._get(url)
            if resp is None:
                break
            repos.extend(r["full_name"] for r in resp.json())
            url = self._next_page(resp)
        return repos

    def _scan_variables(self, repo: str) -> Generator[CiChunk, None, None]:
        resp = self._get(f"{_BASE}/repos/{repo}/actions/variables")
        if resp is None:
            return
        for var in resp.json().get("variables", []):
            yield CiChunk(
                text=var.get("value", ""),
                platform="github",
                repo=repo,
                source_type="variable",
                source_id=var["name"],
            )

    def _scan_logs(self, repo: str) -> Generator[CiChunk, None, None]:
        resp = self._get(
            f"{_BASE}/repos/{repo}/actions/runs?per_page={self._config.max_runs}"
        )
        if resp is None:
            return
        for run in resp.json().get("workflow_runs", []):
            run_id = run["id"]
            jobs_resp = self._get(f"{_BASE}/repos/{repo}/actions/runs/{run_id}/jobs")
            if jobs_resp is None:
                continue
            for job in jobs_resp.json().get("jobs", []):
                job_id = job["id"]
                log_resp = self._get(
                    f"{_BASE}/repos/{repo}/actions/jobs/{job_id}/logs",
                    allow_redirects=True,
                )
                if log_resp and log_resp.status_code == 200:
                    yield CiChunk(
                        text=log_resp.text[:1_000_000],
                        platform="github",
                        repo=repo,
                        source_type="log",
                        source_id=f"run:{run_id}/job:{job_id}",
                    )

    def _get(self, url: str, allow_redirects: bool = False) -> requests.Response | None:
        try:
            resp = self._session.get(url, timeout=30, allow_redirects=allow_redirects)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (401, 403, 404):
                print(f"Warning: HTTP {resp.status_code} for {url}", file=sys.stderr)
            return None
        except requests.RequestException as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            return None

    def _next_page(self, resp: requests.Response) -> str | None:
        for part in resp.headers.get("Link", "").split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None
