# Keyguard — CI Platform Integration (v3)

**Date:** 2026-04-05
**Status:** Approved
**Scope:** v3 of a three-subsystem tool. This spec covers live CI/CD platform scanning. v1 (file scanner) and v2 (GCP API auditor) are complete.

---

## Background

CI/CD platforms are a common source of credential leaks:
1. Developers accidentally `echo` secrets in workflow steps, printing them to run logs
2. Plaintext environment variables (distinct from encrypted secrets) stored directly in CI platforms contain real credentials
3. Masked variable names can reveal what credentials a project uses, even when values are hidden

v1 scans pipeline config *files* (`.github/workflows/*.yml`, `.circleci/config.yml`). v3 scans the *live* CI platforms via their APIs to find credentials in run logs and stored variables — content v1 cannot access.

---

## Architecture

v3 adds a new `keyguard/ci/` package:

```
keyguard/ci/
  __init__.py
  models.py      # CiChunk + CiFinding dataclasses
  github.py      # GitHubCiScanner
  circleci.py    # CircleCiScanner
  gitlab.py      # GitLabCiScanner
  scan.py        # ci_scan() orchestration
  output.py      # CiTerminalReporter + CiJsonExporter
```

**Flow:**

```
.keyguard.toml [ci] tokens + org/group configuration
        ↓
GitHubCiScanner    → CiChunk objects
CircleCiScanner    → CiChunk objects
GitLabCiScanner    → CiChunk objects
        ↓
ci_scan() feeds each CiChunk.text through existing RegexMatcher + RuleLoader
        ↓
CiFinding objects (match result + CI metadata)
        ↓
CiTerminalReporter / CiJsonExporter
```

The detection engine is **identical to v1** — same `RegexMatcher`, same `RuleLoader`, same Google rules, same entropy filter. Only the input sources change. No new rules needed.

---

## Data Models

**`CiChunk`** — what scanners yield:

```python
@dataclass
class CiChunk:
    text: str
    platform: str       # "github" | "circleci" | "gitlab"
    repo: str           # "owner/name" or "group/project"
    source_type: str    # "log" | "variable"
    source_id: str      # job ID / run ID for logs; variable name for variables
```

**`CiFinding`** — result after detection:

```python
@dataclass
class CiFinding:
    platform: str
    repo: str
    source_type: str    # "log" | "variable"
    source_id: str
    rule_id: str
    severity: str       # "critical" | "high" | "info"
    matched_value: str  # redacted in output by default
    entropy: float
    line: int

    def to_dict(self, redact: bool = True) -> dict: ...
```

**Bridge from `CiChunk` to v1's `RegexMatcher`:**

```python
for ci_chunk in scanner.scan():
    chunk = Chunk(text=ci_chunk.text, file_path=ci_chunk.source_id, line_offset=1)
    for finding in matcher.scan(chunk):
        ci_findings.append(CiFinding(
            platform=ci_chunk.platform,
            repo=ci_chunk.repo,
            source_type=ci_chunk.source_type,
            source_id=ci_chunk.source_id,
            rule_id=finding.rule_id,
            severity=finding.severity,
            matched_value=finding.matched_value,
            entropy=finding.entropy,
            line=finding.line,
        ))
```

---

## What Each Scanner Fetches

| Scanner | Variables | Logs |
|---|---|---|
| GitHub | `GET /repos/{owner}/{repo}/actions/variables` — plaintext values, fully scannable | Last N workflow run job logs via `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` |
| CircleCI | `GET /v2/project/{slug}/envvar` — values always masked (`xxxxxx`), scan names only for suspicious patterns | Last N pipeline job step logs |
| GitLab | `GET /api/v4/projects/{id}/variables` — plaintext unless user-masked, fully scannable | Last N pipeline job traces via `GET /api/v4/projects/{id}/jobs/{job_id}/trace` |

**CircleCI variable name scanning:** Since values are masked, variable names matching `GOOGLE_*`, `GEMINI_*`, `GCP_*`, or `FIREBASE_*` emit an informational finding: `severity="info"`, description: *"Masked variable '{name}' detected — verify it does not contain an exposed credential"*.

**Scope resolution per platform:**
- If `repos` is set under `[ci.github]`/`[ci.gitlab]` → scan only those repos
- If `orgs`/`groups` is set → discover all repos in that org/group via API
- Both can be set → union of both

---

## Configuration

**`.keyguard.toml` example:**

```toml
[ci]
# Authentication tokens
github_token    = "ghp_xxxxxxxxxxxxxxxxxxxx"
circleci_token  = "CCIPAT_xxxxxxxxxxxxxxxx"
gitlab_token    = "glpat-xxxxxxxxxxxxxxxxxxxx"
gitlab_url      = "https://gitlab.com"   # override for self-hosted GitLab
max_runs        = 10                     # recent runs/pipelines per repo

[ci.github]
orgs  = ["my-org"]                       # scan all repos in these orgs
repos = ["my-org/specific-repo"]         # OR specific repos (overrides orgs if set)

[ci.circleci]
orgs = ["my-org"]

[ci.gitlab]
groups = ["my-group"]
repos  = ["my-group/specific-repo"]      # OR specific projects
```

---

## CLI Interface

```bash
# Scan all configured platforms
keyguard ci

# Scan one platform only
keyguard ci --platform github
keyguard ci --platform circleci
keyguard ci --platform gitlab

# Narrow to a specific repo
keyguard ci --repo owner/repo-name

# Export JSON
keyguard ci --output json --out-file ci-findings.json
```

**Exit codes:** `0` = clean, `1` = findings detected, `2` = tool error (no tokens configured, API auth failure on all platforms)

---

## Output

**`CiTerminalReporter`:**

```
Platform: GitHub
  Repo: my-org/api-service

  CRITICAL  log       job:build / run:987654321    AIzaSy... found in step output (line 42)
  HIGH      variable  GOOGLE_MAPS_KEY              Plaintext variable contains Google API key

Platform: GitLab
  Repo: my-group/backend

  INFO      variable  GEMINI_API_KEY               Masked variable name suggests stored credential

Found 3 finding(s). Critical: 1, High: 1, Info: 1.
```

**`CiJsonExporter`:** writes JSON array of `CiFinding.to_dict()` objects. No SARIF — CI findings are not file-centric.

---

## Error Handling

| Condition | Behavior |
|---|---|
| Missing token for a platform | Notice: *"Skipping GitHub: no github_token in [ci] config"*, platform skipped |
| Auth failure (401/403) | Warning printed, platform skipped, other platforms continue |
| Repo not accessible | Warning, skip to next repo |
| Log fetch 404 (expired run) | Silently skip — logs have retention limits |
| Rate limiting (429) | Exponential backoff, 3 retries, then warning + skip |
| No platforms configured | Error: *"No CI tokens configured in [ci] section of .keyguard.toml"*, exit 2 |
| All platforms skipped (all auth failures) | Exit 2 |

---

## Testing Strategy

- Each scanner tested independently with mocked `requests.Session` — no real API calls
- `ci_scan()` tested with mock scanners returning controlled `CiChunk` fixtures
- Integration test: `CiChunk` seeded with a real Google API key string → detection engine → `CiFinding` produced
- CLI tested via Click's `CliRunner` with `ci_scan` mocked
- CircleCI variable name pattern matching tested against known patterns (`GOOGLE_*`, `GEMINI_*`, `GCP_*`, `FIREBASE_*`)

**New dependencies:** None — all platforms use REST APIs over `requests` (already a dep). Auth via `Authorization: Bearer {token}` header.

---

## CiConfig + ci_scan() Signatures

**`CiConfig`** — new dataclass added to `keyguard/config.py`; `Config` gets `ci: CiConfig | None = None`:

```python
@dataclass
class CiConfig:
    github_token: str | None = None
    circleci_token: str | None = None
    gitlab_token: str | None = None
    gitlab_url: str = "https://gitlab.com"
    max_runs: int = 10
    github_orgs: list[str] = field(default_factory=list)
    github_repos: list[str] = field(default_factory=list)
    circleci_orgs: list[str] = field(default_factory=list)
    gitlab_groups: list[str] = field(default_factory=list)
    gitlab_repos: list[str] = field(default_factory=list)
```

**`ci_scan()` signature:**

```python
def ci_scan(
    ci_config: CiConfig,
    platform: str | None = None,    # if set, only scan this platform
    repos: list[str] | None = None, # if set, override config repos for all platforms
) -> list[CiFinding]:
```

---

## File Map

| File | Responsibility |
|---|---|
| `keyguard/ci/__init__.py` | Package marker |
| `keyguard/ci/models.py` | `CiChunk` + `CiFinding` dataclasses |
| `keyguard/ci/github.py` | `GitHubCiScanner` — variables + logs |
| `keyguard/ci/circleci.py` | `CircleCiScanner` — variable names + logs |
| `keyguard/ci/gitlab.py` | `GitLabCiScanner` — variables + logs |
| `keyguard/ci/scan.py` | `ci_scan()` — orchestrates scanners + detection |
| `keyguard/ci/output.py` | `CiTerminalReporter` + `CiJsonExporter` |
| `keyguard/cli.py` | Add `ci` command + module-level CI imports |
| `keyguard/config.py` | Extend `Config` with CI config fields |
| `tests/test_ci_models.py` | Unit tests for `CiChunk` + `CiFinding` |
| `tests/test_ci_github.py` | Unit tests for `GitHubCiScanner` |
| `tests/test_ci_circleci.py` | Unit tests for `CircleCiScanner` |
| `tests/test_ci_gitlab.py` | Unit tests for `GitLabCiScanner` |
| `tests/test_ci_scan.py` | Unit tests for `ci_scan()` |
| `tests/test_ci_output.py` | Unit tests for reporters |
| `tests/test_ci_cli.py` | CLI tests via CliRunner |

---

## Out of Scope for v3

- Jenkins, Travis CI, Azure DevOps, Bitbucket Pipelines
- Scanning encrypted CI secrets (not exposed by any platform API)
- Real-time webhook-based alerting on new CI runs
- Storing or diffing findings across runs
