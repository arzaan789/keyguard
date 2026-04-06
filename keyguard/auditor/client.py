from __future__ import annotations
import sys
import time
import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_CRM = "https://cloudresourcemanager.googleapis.com/v1"
_SU = "https://serviceusage.googleapis.com/v1"
_KEYS = "https://apikeys.googleapis.com/v2"


class GcpAuthError(Exception):
    pass


class _SkipProject(Exception):
    pass


class GcpClient:
    def __init__(self, credentials_file: str | None = None) -> None:
        try:
            if credentials_file:
                creds = service_account.Credentials.from_service_account_file(
                    credentials_file, scopes=_SCOPES
                )
            else:
                creds, _ = google.auth.default(scopes=_SCOPES)
        except Exception as exc:
            raise GcpAuthError(str(exc)) from exc
        self._session = AuthorizedSession(creds)

    def list_projects(self) -> list[dict]:
        data = self._get(f"{_CRM}/projects")
        return [
            {"projectId": p["projectId"], "name": p.get("name", p["projectId"])}
            for p in data.get("projects", [])
            if p.get("lifecycleState") == "ACTIVE"
        ]

    def gemini_enabled(self, project_id: str) -> bool:
        try:
            data = self._get(
                f"{_SU}/projects/{project_id}/services"
                "/generativelanguage.googleapis.com"
            )
            return data.get("state") == "ENABLED"
        except _SkipProject:
            return False

    def list_keys(self, project_id: str) -> list[dict]:
        try:
            data = self._get(
                f"{_KEYS}/projects/{project_id}/locations/global/keys"
            )
            return data.get("keys", [])
        except _SkipProject:
            return []

    def _get(self, url: str, retries: int = 3) -> dict:
        for attempt in range(retries):
            resp = self._session.get(url)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                continue
            if resp.status_code in (403, 404):
                print(
                    f"Warning: HTTP {resp.status_code} for {url} — skipping",
                    file=sys.stderr,
                )
                raise _SkipProject(f"HTTP {resp.status_code}")
            resp.raise_for_status()
        print(
            f"Warning: rate limited after {retries} retries for {url} — skipping",
            file=sys.stderr,
        )
        raise _SkipProject(f"rate limited: {url}")
