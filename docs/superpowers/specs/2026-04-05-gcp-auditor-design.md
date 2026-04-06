# Keyguard — GCP API Auditor (v2)

**Date:** 2026-04-05
**Status:** Approved
**Scope:** v2 of a three-subsystem tool. This spec covers live GCP project auditing. v1 (file scanner) is complete. v3 will add live CI platform integration.

---

## Background

Google retroactively enabled Gemini API access on existing API keys (e.g., Maps keys) that were designed to be public and embedded in client-side code. When a team member enables Gemini in the same GCP project, unrestricted keys silently become Gemini credentials — exposing projects to unauthorized AI usage and $80k+ billing incidents.

v1 finds credential strings in codebases and git history. v2 answers a complementary question: **"In your live GCP projects, which API keys are dangerous right now?"** It detects keys that are either unrestricted or explicitly allow Gemini while `generativelanguage.googleapis.com` is enabled on the project.

v2 is standalone — it does not cross-reference with v1 file findings (the GCP API Keys API does not return key values, making automated correlation impractical without elevated `apikeys.keys.getKeyString` permissions).

---

## Architecture

v2 adds a new `keyguard/auditor/` package:

```
keyguard/auditor/
  __init__.py
  client.py      # GcpClient — auth + 3 API calls
  audit.py       # audit_projects() + GcpFinding dataclass
  output.py      # GcpTerminalReporter + GcpJsonExporter
```

**Flow:**

```
Auth (ADC or explicit key file)
        ↓
GcpClient.list_projects()       → list of project IDs/names
        ↓ (per project)
GcpClient.gemini_enabled()      → bool
GcpClient.list_keys()           → list of key metadata
        ↓
audit_projects()                → filters for dangerous key+Gemini combos
        ↓
list[GcpFinding]
        ↓
GcpTerminalReporter / GcpJsonExporter
```

**Three GCP API calls per project:**

| API | Endpoint | Purpose |
|---|---|---|
| Cloud Resource Manager v1 | `GET /v1/projects` | Discover all accessible projects |
| Service Usage API v1 | `GET /v1/projects/{id}/services/generativelanguage.googleapis.com` | Check Gemini enabled |
| API Keys API v2 | `GET /v2/projects/{id}/locations/global/keys` | List keys with restrictions |

Auth uses `google-auth` + `google.auth.transport.requests.AuthorizedSession`, which wraps the existing `requests` dependency with automatic token refresh.

---

## GcpClient

`keyguard/auditor/client.py` — thin wrapper that holds an authenticated session and exposes exactly three methods:

```python
class GcpClient:
    def __init__(self, credentials_file: str | None = None) -> None:
        # If credentials_file is given, load service account key
        # Otherwise use Application Default Credentials (ADC)
        ...

    def list_projects(self) -> list[dict]:
        # Returns [{projectId: str, name: str}, ...] for ACTIVE projects only
        ...

    def gemini_enabled(self, project_id: str) -> bool:
        # Returns True if generativelanguage.googleapis.com state == ENABLED
        ...

    def list_keys(self, project_id: str) -> list[dict]:
        # Returns [{name: str, displayName: str, restrictions: dict | None}, ...]
        ...
```

Auth scopes required: `https://www.googleapis.com/auth/cloud-platform`

---

## GcpFinding + Audit Logic

**`GcpFinding`** — new dataclass, distinct from v1's `Finding`:

```python
@dataclass
class GcpFinding:
    project_id: str
    project_name: str
    key_id: str              # short ID extracted from resource name
    key_display_name: str
    restriction: str         # "none" | "gemini_explicit"
    severity: str            # "critical" | "high"
    description: str

    def to_dict(self) -> dict: ...
```

**Severity logic in `audit_projects()`:**

A key is flagged only when **Gemini is enabled on the project** AND one of:

| Condition | `restriction` | `severity` |
|---|---|---|
| Key has no restrictions at all | `"none"` | `"critical"` — silent Maps→Gemini upgrade scenario |
| Key explicitly allows `generativelanguage.googleapis.com` | `"gemini_explicit"` | `"high"` — intentional but potentially embedded in client code |

Keys restricted to unrelated services (e.g., Maps-only restriction) are **not flagged**. Projects where Gemini is disabled are skipped entirely — no findings generated.

**`audit_projects(client: GcpClient, project_ids: list[str] | None = None) -> list[GcpFinding]`:**
- `client` is passed in (dependency injection — makes unit testing without real GCP calls straightforward)
- If `project_ids` is None: calls `client.list_projects()` for auto-discovery
- If `project_ids` is provided: audits only those projects (from `--project` CLI flags)

---

## CLI Interface

New `keyguard audit` command added to `keyguard/cli.py`:

```bash
# Discover and audit all accessible projects (auto-discovery)
keyguard audit

# Audit specific project(s) only
keyguard audit --project my-project-id --project another-project

# Use service account key instead of ADC
keyguard audit --gcp-credentials /path/to/key.json

# Export JSON findings
keyguard audit --output json --out-file gcp-findings.json

# Combined
keyguard audit --gcp-credentials key.json --output json --out-file report.json
```

**Exit codes:** `0` = no findings, `1` = findings detected, `2` = tool error (auth failure, no projects accessible)

---

## Output

**`GcpTerminalReporter`** (terminal always on):

```
Project: my-app-prod (my-project-id)
  Gemini API: ENABLED

  CRITICAL  none              keyguard-maps-key    no API restrictions — any enabled API accessible
  HIGH      gemini_explicit   gemini-dev-key       explicitly allows generativelanguage.googleapis.com

Found 2 finding(s) across 3 projects audited.
```

**`GcpJsonExporter`** (opt-in via `--output json --out-file`):
Writes a JSON array of `GcpFinding.to_dict()` objects. No SARIF — SARIF is file-centric and does not map to cloud resources.

---

## Error Handling

| Condition | Behavior |
|---|---|
| No GCP credentials found | Error: "Run `gcloud auth application-default login` or pass `--gcp-credentials`", exit 2 |
| Invalid credentials file path/format | Error with file path, exit 2 |
| Project 403 (not accessible) | Warning printed, project skipped, audit continues |
| API Keys API not enabled on project | Warning printed, project skipped, audit continues |
| Rate limiting (429) | Exponential backoff, 3 retries, then warning + skip project |
| No projects discovered (auth succeeded, but account has no projects) | Informational message "No accessible projects found", exit 0 — not an error |

---

## Testing Strategy

- `GcpClient` methods tested by mocking `AuthorizedSession.get()` with `unittest.mock` — no real GCP calls
- `audit_projects()` tested with a mock `GcpClient` returning controlled fixture data
- Key test scenarios:
  - Unrestricted key + Gemini enabled → critical finding
  - Restricted (Maps-only) key + Gemini enabled → no finding
  - Gemini disabled → no findings regardless of key restrictions
  - Gemini-explicit key → high finding
  - Project returns 403 → warning, skipped, no crash
- CLI tested via Click's `CliRunner` with `audit_projects` mocked

**New dependency:** `google-auth>=2.0` — auth library only. Requests transport uses existing `requests` dep.

---

## File Map

| File | Responsibility |
|---|---|
| `keyguard/auditor/__init__.py` | Package marker |
| `keyguard/auditor/client.py` | `GcpClient` — auth + 3 GCP API calls |
| `keyguard/auditor/audit.py` | `GcpFinding` dataclass + `audit_projects()` |
| `keyguard/auditor/output.py` | `GcpTerminalReporter` + `GcpJsonExporter` |
| `tests/test_gcp_client.py` | Unit tests for `GcpClient` (mocked HTTP) |
| `tests/test_gcp_audit.py` | Unit tests for `audit_projects()` (mocked client) |
| `tests/test_gcp_output.py` | Unit tests for reporters |
| `tests/test_gcp_cli.py` | CLI tests via CliRunner |

---

## Out of Scope for v2

- Cross-referencing GCP key findings with v1 file findings
- Auditing other GCP services beyond Gemini
- Auditing IAM permissions or service account keys
- Live CI platform integration (v3)
