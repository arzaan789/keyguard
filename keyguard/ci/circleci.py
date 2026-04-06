from __future__ import annotations
import re
import sys
from typing import Generator
import requests
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig

_BASE_V2 = "https://circleci.com/api/v2"
_BASE_V1 = "https://circleci.com/api/v1.1"
_SUSPICIOUS_NAME = re.compile(
    r"(GOOGLE|GEMINI|GCP|FIREBASE|GCLOUD|VERTEX)", re.IGNORECASE
)


class CircleCiScanner:
    def __init__(self, config: CiConfig, repos_override: list[str] | None = None) -> None:
        self._config = config
        self._repos_override = repos_override
        self._session = requests.Session()
        self._session.headers.update({"Circle-Token": config.circleci_token})

    def scan(self) -> Generator[CiChunk, None, None]:
        for slug in self._resolve_slugs():
            yield from self._scan_variables(slug)
            yield from self._scan_logs(slug)

    def _resolve_slugs(self) -> list[str]:
        # slug format: "github/{org}/{repo}"
        if self._repos_override:
            return self._repos_override
        slugs: list[str] = []
        for org in self._config.circleci_orgs:
            slugs.extend(self._list_org_slugs(org))
        return slugs

    def _list_org_slugs(self, org: str) -> list[str]:
        resp = self._get(f"{_BASE_V2}/me/collaborations")
        if resp is None:
            return []
        return [
            f"github/{org}/{c['name']}"
            for c in resp.json()
            if c.get("slug", "").split("/")[0] == org
        ]

    def _scan_variables(self, slug: str) -> Generator[CiChunk, None, None]:
        resp = self._get(f"{_BASE_V2}/project/{slug}/envvar")
        if resp is None:
            return
        for var in resp.json():
            name = var.get("name", "")
            if _SUSPICIOUS_NAME.search(name):
                yield CiChunk(
                    text=name,
                    platform="circleci",
                    repo=slug,
                    source_type="variable",
                    source_id=name,
                    is_name_only=True,
                )

    def _scan_logs(self, slug: str) -> Generator[CiChunk, None, None]:
        resp = self._get(
            f"{_BASE_V2}/project/{slug}/pipeline?limit={self._config.max_runs}"
        )
        if resp is None:
            return
        for pipeline in resp.json().get("items", []):
            pipe_id = pipeline["id"]
            wf_resp = self._get(f"{_BASE_V2}/pipeline/{pipe_id}/workflow")
            if wf_resp is None:
                continue
            for wf in wf_resp.json().get("items", []):
                jobs_resp = self._get(f"{_BASE_V2}/workflow/{wf['id']}/job")
                if jobs_resp is None:
                    continue
                for job in jobs_resp.json().get("items", []):
                    job_num = job.get("job_number")
                    if job_num is None:
                        continue
                    log_resp = self._get(f"{_BASE_V1}/project/{slug}/{job_num}/output")
                    if log_resp is None:
                        continue
                    text = self._extract_log_text(log_resp)
                    if text:
                        yield CiChunk(
                            text=text[:1_000_000],
                            platform="circleci",
                            repo=slug,
                            source_type="log",
                            source_id=f"pipeline:{pipe_id}/job:{job_num}",
                        )

    def _extract_log_text(self, resp: requests.Response) -> str:
        try:
            steps = resp.json()
            lines: list[str] = []
            for step in steps:
                for action in step.get("actions", []):
                    lines.append(action.get("message", ""))
            return "\n".join(lines)
        except Exception:
            return resp.text

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
