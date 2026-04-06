# Keyguard GCP API Auditor (v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `keyguard audit` — a CLI command that discovers all accessible GCP projects and flags API keys that have Gemini access (either unrestricted or explicitly allowing `generativelanguage.googleapis.com`) while Gemini is enabled on the project.

**Architecture:** A `GcpClient` class (thin wrapper over `google-auth` + `requests`) exposes three API call methods. `audit_projects(client, project_ids)` uses the client to discover projects, check Gemini state, list keys, and produce `GcpFinding` objects. Output is routed to `GcpTerminalReporter` and optionally `GcpJsonExporter`. The `keyguard audit` CLI command wires everything together. All components follow the same patterns as v1.

**Tech Stack:** Python 3.11+, google-auth>=2.0 (auth), requests (existing dep, used via AuthorizedSession transport), Rich (existing dep, terminal output), Click (existing dep, CLI), unittest.mock (test mocking — no real GCP calls)

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Add `google-auth>=2.0` dependency |
| `keyguard/auditor/__init__.py` | Package marker |
| `keyguard/auditor/client.py` | `GcpClient`, `GcpAuthError`, `_SkipProject` |
| `keyguard/auditor/audit.py` | `GcpFinding` dataclass + `audit_projects()` |
| `keyguard/auditor/output.py` | `GcpTerminalReporter` + `GcpJsonExporter` |
| `keyguard/cli.py` | Add module-level auditor imports + `audit` command |
| `tests/test_gcp_client.py` | Unit tests for `GcpClient` (mocked HTTP) |
| `tests/test_gcp_audit.py` | Unit tests for `GcpFinding` + `audit_projects()` |
| `tests/test_gcp_output.py` | Unit tests for both reporters |
| `tests/test_gcp_cli.py` | CLI integration tests via `CliRunner` |

---

## Task 1: Add Dependency + Package Skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `keyguard/auditor/__init__.py`
- Create: `keyguard/auditor/client.py` (empty)
- Create: `keyguard/auditor/audit.py` (empty)
- Create: `keyguard/auditor/output.py` (empty)

- [ ] **Step 1: Add `google-auth` to `pyproject.toml` dependencies**

In `pyproject.toml`, add `"google-auth>=2.0",` to the `dependencies` list:

```toml
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "gitpython>=3.1",
    "pathspec>=0.12",
    "watchdog>=4.0",
    "requests>=2.31",
    "google-auth>=2.0",
]
```

- [ ] **Step 2: Create auditor package**

Create these files (all empty stubs):
```
keyguard/auditor/__init__.py   → (empty)
keyguard/auditor/client.py     → (empty)
keyguard/auditor/audit.py      → (empty)
keyguard/auditor/output.py     → (empty)
```

- [ ] **Step 3: Install the updated package**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pip install -e ".[dev]"
```

Expected: `google-auth` installs, no errors.

- [ ] **Step 4: Verify all existing tests still pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest -q
```

Expected: 69 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml keyguard/auditor/
git commit -m "chore: add google-auth dep and auditor package skeleton"
```

---

## Task 2: GcpFinding Dataclass

**Files:**
- Modify: `keyguard/auditor/audit.py`
- Create: `tests/test_gcp_audit.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gcp_audit.py`:

```python
from keyguard.auditor.audit import GcpFinding


def test_gcp_finding_fields():
    f = GcpFinding(
        project_id="my-project",
        project_name="My Project",
        key_id="abc123",
        key_display_name="Maps Key",
        restriction="none",
        severity="critical",
        description="No restrictions.",
    )
    assert f.project_id == "my-project"
    assert f.severity == "critical"
    assert f.restriction == "none"


def test_gcp_finding_to_dict():
    f = GcpFinding(
        project_id="my-project",
        project_name="My Project",
        key_id="abc123",
        key_display_name="Maps Key",
        restriction="none",
        severity="critical",
        description="No restrictions.",
    )
    d = f.to_dict()
    assert d["project_id"] == "my-project"
    assert d["project_name"] == "My Project"
    assert d["key_id"] == "abc123"
    assert d["key_display_name"] == "Maps Key"
    assert d["restriction"] == "none"
    assert d["severity"] == "critical"
    assert d["description"] == "No restrictions."


def test_gcp_finding_to_dict_has_all_keys():
    f = GcpFinding(
        project_id="p", project_name="P", key_id="k",
        key_display_name="K", restriction="none",
        severity="critical", description="D",
    )
    d = f.to_dict()
    assert set(d.keys()) == {
        "project_id", "project_name", "key_id", "key_display_name",
        "restriction", "severity", "description",
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_audit.py -v
```

Expected: `ImportError: cannot import name 'GcpFinding'`

- [ ] **Step 3: Implement `GcpFinding` in `keyguard/auditor/audit.py`**

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GcpFinding:
    project_id: str
    project_name: str
    key_id: str
    key_display_name: str
    restriction: str    # "none" | "gemini_explicit"
    severity: str       # "critical" | "high"
    description: str

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "key_id": self.key_id,
            "key_display_name": self.key_display_name,
            "restriction": self.restriction,
            "severity": self.severity,
            "description": self.description,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_audit.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/auditor/audit.py tests/test_gcp_audit.py
git commit -m "feat: add GcpFinding dataclass"
```

---

## Task 3: GcpClient

**Files:**
- Modify: `keyguard/auditor/client.py`
- Create: `tests/test_gcp_client.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gcp_client.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from keyguard.auditor.client import GcpClient, GcpAuthError


def _mock_response(status_code: int, data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_projects_returns_active_only(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {
        "projects": [
            {"projectId": "proj-a", "name": "Active",   "lifecycleState": "ACTIVE"},
            {"projectId": "proj-b", "name": "Deleted",  "lifecycleState": "DELETE_REQUESTED"},
        ]
    })
    client = GcpClient()
    projects = client.list_projects()
    assert len(projects) == 1
    assert projects[0]["projectId"] == "proj-a"
    assert projects[0]["name"] == "Active"


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_returns_true(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {"state": "ENABLED"})
    assert GcpClient().gemini_enabled("my-project") is True


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_returns_false_when_disabled(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {"state": "DISABLED"})
    assert GcpClient().gemini_enabled("my-project") is False


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_gemini_enabled_403_returns_false(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(403, {})
    assert GcpClient().gemini_enabled("my-project") is False


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_keys_returns_keys(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {
        "keys": [{"name": "projects/1/locations/global/keys/abc",
                  "displayName": "My Key", "restrictions": None}]
    })
    keys = GcpClient().list_keys("my-project")
    assert len(keys) == 1
    assert keys[0]["displayName"] == "My Key"


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_keys_403_returns_empty(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(403, {})
    assert GcpClient().list_keys("my-project") == []


@patch("keyguard.auditor.client.AuthorizedSession")
@patch("keyguard.auditor.client.google.auth.default")
def test_list_projects_empty_when_no_projects_key(mock_default, mock_session_cls):
    mock_default.return_value = (MagicMock(), "proj")
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _mock_response(200, {})
    assert GcpClient().list_projects() == []


@patch("keyguard.auditor.client.service_account.Credentials.from_service_account_file")
def test_invalid_credentials_file_raises_auth_error(mock_creds):
    mock_creds.side_effect = FileNotFoundError("not found")
    with pytest.raises(GcpAuthError):
        GcpClient(credentials_file="/nonexistent/key.json")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_client.py -v
```

Expected: `ImportError: cannot import name 'GcpClient'`

- [ ] **Step 3: Implement `keyguard/auditor/client.py`**

```python
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
                raise _SkipProject(f"HTTP {resp.status_code} for {url}")
            resp.raise_for_status()
        raise _SkipProject(f"rate limited after {retries} retries: {url}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_client.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/auditor/client.py tests/test_gcp_client.py
git commit -m "feat: add GcpClient with auth and GCP API calls"
```

---

## Task 4: audit_projects() Function

**Files:**
- Modify: `keyguard/auditor/audit.py` (add `audit_projects`)
- Modify: `tests/test_gcp_audit.py` (append tests)

- [ ] **Step 1: Append these failing tests to `tests/test_gcp_audit.py`**

```python
from unittest.mock import MagicMock
from keyguard.auditor.audit import GcpFinding, audit_projects


def _make_client(
    projects=None,
    gemini_states=None,
    keys_by_project=None,
) -> MagicMock:
    client = MagicMock()
    client.list_projects.return_value = projects or []
    client.gemini_enabled.side_effect = (
        lambda pid: (gemini_states or {}).get(pid, False)
    )
    client.list_keys.side_effect = (
        lambda pid: (keys_by_project or {}).get(pid, [])
    )
    return client


def _unrestricted_key(display_name: str = "Maps Key") -> dict:
    return {
        "name": "projects/123/locations/global/keys/abc",
        "displayName": display_name,
        "restrictions": None,
    }


def _gemini_key(display_name: str = "Gemini Key") -> dict:
    return {
        "name": "projects/123/locations/global/keys/xyz",
        "displayName": display_name,
        "restrictions": {
            "apiTargets": [{"service": "generativelanguage.googleapis.com"}]
        },
    }


def _maps_only_key() -> dict:
    return {
        "name": "projects/123/locations/global/keys/maps",
        "displayName": "Maps Only",
        "restrictions": {
            "apiTargets": [{"service": "maps-backend.googleapis.com"}]
        },
    }


def test_unrestricted_key_gemini_enabled_is_critical():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].restriction == "none"
    assert findings[0].project_id == "proj-a"
    assert findings[0].key_display_name == "Maps Key"


def test_gemini_explicit_key_is_high():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_gemini_key()]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].restriction == "gemini_explicit"


def test_maps_only_key_not_flagged():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_maps_only_key()]},
    )
    assert audit_projects(client) == []


def test_gemini_disabled_no_findings():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": False},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    assert audit_projects(client) == []


def test_specific_project_ids_skips_discovery():
    client = _make_client(
        gemini_states={"specific-proj": True},
        keys_by_project={"specific-proj": [_unrestricted_key()]},
    )
    findings = audit_projects(client, project_ids=["specific-proj"])
    client.list_projects.assert_not_called()
    assert len(findings) == 1
    assert findings[0].project_id == "specific-proj"


def test_empty_restrictions_dict_treated_as_unrestricted():
    key = {
        "name": "projects/123/locations/global/keys/abc",
        "displayName": "Empty Restrict Key",
        "restrictions": {},
    }
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [key]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].restriction == "none"


def test_key_id_extracted_from_resource_name():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    findings = audit_projects(client)
    assert findings[0].key_id == "abc"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_audit.py -k "test_unrestricted_key" -v
```

Expected: `ImportError: cannot import name 'audit_projects'`

- [ ] **Step 3: Add `audit_projects()` to `keyguard/auditor/audit.py`**

Append after the `GcpFinding` class (keep the existing import and dataclass, add below):

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from keyguard.auditor.client import GcpClient

# ... GcpFinding dataclass stays above ...

def audit_projects(
    client: GcpClient,
    project_ids: list[str] | None = None,
) -> list[GcpFinding]:
    if project_ids is None:
        projects = client.list_projects()
    else:
        projects = [{"projectId": pid, "name": pid} for pid in project_ids]

    findings: list[GcpFinding] = []

    for project in projects:
        pid = project["projectId"]
        pname = project["name"]

        if not client.gemini_enabled(pid):
            continue

        for key in client.list_keys(pid):
            key_name = key.get("name", "")
            key_id = key_name.rsplit("/", 1)[-1] if key_name else "unknown"
            key_display = key.get("displayName", key_id)
            restrictions = key.get("restrictions") or {}
            api_targets = restrictions.get("apiTargets", [])

            if not api_targets:
                # No api targets → unrestricted → silent Gemini access
                findings.append(GcpFinding(
                    project_id=pid,
                    project_name=pname,
                    key_id=key_id,
                    key_display_name=key_display,
                    restriction="none",
                    severity="critical",
                    description=(
                        f"Key '{key_display}' has no API restrictions and Gemini is enabled "
                        f"on project '{pid}' — any API including Gemini is accessible."
                    ),
                ))
            else:
                gemini_targets = [
                    t for t in api_targets
                    if t.get("service") == "generativelanguage.googleapis.com"
                ]
                if gemini_targets:
                    findings.append(GcpFinding(
                        project_id=pid,
                        project_name=pname,
                        key_id=key_id,
                        key_display_name=key_display,
                        restriction="gemini_explicit",
                        severity="high",
                        description=(
                            f"Key '{key_display}' explicitly allows "
                            f"generativelanguage.googleapis.com on project '{pid}'."
                        ),
                    ))

    return findings
```

The full `keyguard/auditor/audit.py` file must look like this (replace the entire file):

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GcpFinding:
    project_id: str
    project_name: str
    key_id: str
    key_display_name: str
    restriction: str    # "none" | "gemini_explicit"
    severity: str       # "critical" | "high"
    description: str

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "key_id": self.key_id,
            "key_display_name": self.key_display_name,
            "restriction": self.restriction,
            "severity": self.severity,
            "description": self.description,
        }


def audit_projects(
    client: "GcpClient",  # noqa: F821 — avoid circular import
    project_ids: list[str] | None = None,
) -> list[GcpFinding]:
    if project_ids is None:
        projects = client.list_projects()
    else:
        projects = [{"projectId": pid, "name": pid} for pid in project_ids]

    findings: list[GcpFinding] = []

    for project in projects:
        pid = project["projectId"]
        pname = project["name"]

        if not client.gemini_enabled(pid):
            continue

        for key in client.list_keys(pid):
            key_name = key.get("name", "")
            key_id = key_name.rsplit("/", 1)[-1] if key_name else "unknown"
            key_display = key.get("displayName", key_id)
            restrictions = key.get("restrictions") or {}
            api_targets = restrictions.get("apiTargets", [])

            if not api_targets:
                findings.append(GcpFinding(
                    project_id=pid,
                    project_name=pname,
                    key_id=key_id,
                    key_display_name=key_display,
                    restriction="none",
                    severity="critical",
                    description=(
                        f"Key '{key_display}' has no API restrictions and Gemini is enabled "
                        f"on project '{pid}' — any API including Gemini is accessible."
                    ),
                ))
            else:
                gemini_targets = [
                    t for t in api_targets
                    if t.get("service") == "generativelanguage.googleapis.com"
                ]
                if gemini_targets:
                    findings.append(GcpFinding(
                        project_id=pid,
                        project_name=pname,
                        key_id=key_id,
                        key_display_name=key_display,
                        restriction="gemini_explicit",
                        severity="high",
                        description=(
                            f"Key '{key_display}' explicitly allows "
                            f"generativelanguage.googleapis.com on project '{pid}'."
                        ),
                    ))

    return findings
```

- [ ] **Step 4: Run all gcp_audit tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_audit.py -v
```

Expected: all 10 tests pass (3 from Task 2 + 7 new).

- [ ] **Step 5: Commit**

```bash
git add keyguard/auditor/audit.py tests/test_gcp_audit.py
git commit -m "feat: add audit_projects() with severity logic"
```

---

## Task 5: GcpTerminalReporter + GcpJsonExporter

**Files:**
- Modify: `keyguard/auditor/output.py`
- Create: `tests/test_gcp_output.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gcp_output.py`:

```python
import json
from io import StringIO
from rich.console import Console
from keyguard.auditor.audit import GcpFinding
from keyguard.auditor.output import GcpTerminalReporter, GcpJsonExporter


def _make_finding(**kwargs) -> GcpFinding:
    defaults = dict(
        project_id="my-project",
        project_name="My Project",
        key_id="abc123",
        key_display_name="Maps Key",
        restriction="none",
        severity="critical",
        description="No restrictions.",
    )
    defaults.update(kwargs)
    return GcpFinding(**defaults)


def _capture(findings) -> str:
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    GcpTerminalReporter(console=console).report(findings)
    return buf.getvalue()


def test_terminal_shows_project_id():
    assert "my-project" in _capture([_make_finding()])


def test_terminal_shows_key_display_name():
    assert "Maps Key" in _capture([_make_finding()])


def test_terminal_shows_severity():
    assert "CRITICAL" in _capture([_make_finding()])


def test_terminal_shows_restriction():
    assert "none" in _capture([_make_finding()])


def test_terminal_no_findings_shows_clean():
    output = _capture([])
    assert "No GCP findings" in output


def test_terminal_shows_count():
    output = _capture([_make_finding(), _make_finding(severity="high", restriction="gemini_explicit")])
    assert "2" in output


def test_json_exporter_writes_valid_json(tmp_path):
    out = tmp_path / "report.json"
    GcpJsonExporter(out_file=str(out)).report([_make_finding()])
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["project_id"] == "my-project"
    assert data[0]["severity"] == "critical"


def test_json_exporter_empty_writes_empty_list(tmp_path):
    out = tmp_path / "report.json"
    GcpJsonExporter(out_file=str(out)).report([])
    assert json.loads(out.read_text()) == []


def test_json_exporter_all_fields_present(tmp_path):
    out = tmp_path / "report.json"
    GcpJsonExporter(out_file=str(out)).report([_make_finding()])
    data = json.loads(out.read_text())
    assert set(data[0].keys()) == {
        "project_id", "project_name", "key_id", "key_display_name",
        "restriction", "severity", "description",
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_output.py -v
```

Expected: `ImportError: cannot import name 'GcpTerminalReporter'`

- [ ] **Step 3: Implement `keyguard/auditor/output.py`**

```python
from __future__ import annotations
import json
from rich.console import Console
from rich.table import Table
from rich import box
from keyguard.auditor.audit import GcpFinding

_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
}


class GcpTerminalReporter:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def report(self, findings: list[GcpFinding]) -> None:
        if not findings:
            self._console.print("[green]No GCP findings detected.[/green]")
            return

        by_project: dict[str, list[GcpFinding]] = {}
        for f in findings:
            by_project.setdefault(f.project_id, []).append(f)

        for project_id, pfindings in by_project.items():
            pname = pfindings[0].project_name
            self._console.print(f"\nProject: {pname} ({project_id})")
            self._console.print("  Gemini API: ENABLED")

            table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
            table.add_column("Severity")
            table.add_column("Restriction")
            table.add_column("Key")
            table.add_column("Description")

            for f in pfindings:
                color = _SEVERITY_COLORS.get(f.severity, "white")
                table.add_row(
                    f"[{color}]{f.severity.upper()}[/{color}]",
                    f.restriction,
                    f.key_display_name,
                    f.description,
                )
            self._console.print(table)

        critical = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        self._console.print(
            f"Found {len(findings)} finding(s). "
            f"Critical: {critical}, High: {high}."
        )


class GcpJsonExporter:
    def __init__(self, out_file: str) -> None:
        self._out_file = out_file

    def report(self, findings: list[GcpFinding]) -> None:
        with open(self._out_file, "w") as fh:
            json.dump([f.to_dict() for f in findings], fh, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_output.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/auditor/output.py tests/test_gcp_output.py
git commit -m "feat: add GcpTerminalReporter and GcpJsonExporter"
```

---

## Task 6: CLI audit Command

**Files:**
- Modify: `keyguard/cli.py` (add module-level imports + `audit` command)
- Create: `tests/test_gcp_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gcp_cli.py`:

```python
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from keyguard.cli import main
from keyguard.auditor.audit import GcpFinding


def _make_finding(**kwargs) -> GcpFinding:
    defaults = dict(
        project_id="my-project",
        project_name="My Project",
        key_id="abc123",
        key_display_name="Maps Key",
        restriction="none",
        severity="critical",
        description="No restrictions.",
    )
    defaults.update(kwargs)
    return GcpFinding(**defaults)


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_no_findings_exits_zero(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 0


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_with_findings_exits_one(mock_client_cls, mock_audit):
    mock_audit.return_value = [_make_finding()]
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 1


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_output_contains_project_id(mock_client_cls, mock_audit):
    mock_audit.return_value = [_make_finding()]
    result = CliRunner().invoke(main, ["audit"])
    assert "my-project" in result.output


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_specific_project_passed_to_audit(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    CliRunner().invoke(main, ["audit", "--project", "specific-proj"])
    _, kwargs = mock_audit.call_args
    assert kwargs["project_ids"] == ["specific-proj"]


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_no_project_flag_passes_none(mock_client_cls, mock_audit):
    mock_audit.return_value = []
    CliRunner().invoke(main, ["audit"])
    _, kwargs = mock_audit.call_args
    assert kwargs["project_ids"] is None


@patch("keyguard.cli.GcpClient")
def test_audit_auth_error_exits_two(mock_client_cls):
    from keyguard.auditor.client import GcpAuthError
    mock_client_cls.side_effect = GcpAuthError("No credentials")
    result = CliRunner().invoke(main, ["audit"])
    assert result.exit_code == 2


@patch("keyguard.cli.audit_projects")
@patch("keyguard.cli.GcpClient")
def test_audit_json_output_writes_file(mock_client_cls, mock_audit, tmp_path):
    mock_audit.return_value = [_make_finding()]
    out = tmp_path / "gcp.json"
    CliRunner().invoke(
        main, ["audit", "--output", "json", "--out-file", str(out)]
    )
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data[0]["project_id"] == "my-project"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_cli.py -v
```

Expected: `No such command 'audit'` or import error.

- [ ] **Step 3: Add module-level imports to `keyguard/cli.py`**

At the top of `keyguard/cli.py`, after the existing imports, add:

```python
from keyguard.auditor.client import GcpClient, GcpAuthError
from keyguard.auditor.audit import audit_projects
from keyguard.auditor.output import GcpTerminalReporter, GcpJsonExporter
```

- [ ] **Step 4: Append `audit` command to `keyguard/cli.py`** (after the existing `config` group):

```python
@main.command()
@click.option(
    "--project", "project_ids", multiple=True,
    help="GCP project ID to audit (repeatable). Default: auto-discover all.",
)
@click.option(
    "--gcp-credentials", default=None,
    help="Path to service account JSON key. Default: Application Default Credentials.",
)
@click.option(
    "--output", "output_formats", multiple=True,
    type=click.Choice(["json"]),
    help="Additional output format. Terminal is always on.",
)
@click.option("--out-file", default=None, help="Path for JSON output file.")
def audit(project_ids, gcp_credentials, output_formats, out_file) -> None:
    """Audit GCP projects for API keys with Gemini access."""
    try:
        client = GcpClient(credentials_file=gcp_credentials or None)
    except GcpAuthError as exc:
        click.echo(
            f"Error: {exc}\n"
            "Run `gcloud auth application-default login` "
            "or pass `--gcp-credentials key.json`",
            err=True,
        )
        sys.exit(2)

    project_list = list(project_ids) if project_ids else None
    findings = audit_projects(client, project_ids=project_list)

    GcpTerminalReporter().report(findings)

    if "json" in output_formats and out_file:
        GcpJsonExporter(out_file=out_file).report(findings)

    sys.exit(1 if findings else 0)
```

- [ ] **Step 5: Run all GCP CLI tests**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_gcp_cli.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 6: Run full test suite to confirm no regressions**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest -v --tb=short
```

Expected: all tests pass (69 existing + new GCP tests).

- [ ] **Step 7: Commit**

```bash
git add keyguard/cli.py tests/test_gcp_cli.py
git commit -m "feat: add keyguard audit CLI command for GCP API key auditing"
```

---

## Self-Review

**Spec coverage:**
- `GcpClient` with ADC + explicit credentials ✓ Task 3
- Auto-discover all projects (`list_projects`) ✓ Task 3 + 4
- Check Gemini enabled per project ✓ Task 3 + 4
- List keys per project ✓ Task 3 + 4
- Unrestricted key + Gemini → critical finding ✓ Task 4
- Gemini-explicit key → high finding ✓ Task 4
- Maps-only key not flagged ✓ Task 4
- Gemini disabled → no findings ✓ Task 4
- `--project` flag to override discovery ✓ Task 6
- `--gcp-credentials` flag ✓ Task 6
- Terminal output (always on) ✓ Task 5 + 6
- JSON output (opt-in) ✓ Task 5 + 6
- Exit 0 / 1 / 2 ✓ Task 6
- Auth error → clear message + exit 2 ✓ Task 6
- 403/404 per project → warning, skip (handled in GcpClient returning empty/False) ✓ Task 3
- Rate limiting → exponential backoff ✓ Task 3
- `GcpFinding.to_dict()` with all 7 keys ✓ Task 2

**Note on warnings for skipped projects:** The current `GcpClient` silently returns empty/False on 403/404. The spec says "Warning printed, project skipped." Add a `print(f"Warning: ...", file=sys.stderr)` call in `list_keys` and `gemini_enabled` before returning empty/False on 403/404. This is a small addition to Task 3's implementation — implementer should add this to `client.py`.

Fix: In `_get()`, before raising `_SkipProject`, print a warning:

```python
if resp.status_code in (403, 404):
    print(f"Warning: HTTP {resp.status_code} for {url} — skipping", file=sys.stderr)
    raise _SkipProject(f"HTTP {resp.status_code}")
```
