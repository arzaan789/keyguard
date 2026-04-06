# Keyguard CI Platform Integration (v3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `keyguard ci` — a command that scans GitHub Actions, CircleCI, and GitLab CI for exposed Google API credentials in workflow run logs and stored variables.

**Architecture:** Three platform scanners yield `CiChunk` objects (text + CI metadata). `ci_scan()` feeds each chunk through the existing v1 `RegexMatcher` + `RuleLoader` and wraps results as `CiFinding` objects. No new detection logic — only new input sources. `CiConfig` is added to the existing `Config` dataclass and parsed from `.keyguard.toml`.

**Tech Stack:** Python 3.11+, requests (existing dep), unittest.mock (testing — no real API calls), Click (existing dep), Rich (existing dep)

---

## Task 1: CI Package Skeleton

**Files:**
- Create: `keyguard/ci/__init__.py`
- Create: `keyguard/ci/models.py` (empty)
- Create: `keyguard/ci/github.py` (empty)
- Create: `keyguard/ci/circleci.py` (empty)
- Create: `keyguard/ci/gitlab.py` (empty)
- Create: `keyguard/ci/scan.py` (empty)
- Create: `keyguard/ci/output.py` (empty)

- [ ] **Step 1: Create the package and empty stubs**

```
keyguard/ci/__init__.py   → (empty)
keyguard/ci/models.py     → (empty)
keyguard/ci/github.py     → (empty)
keyguard/ci/circleci.py   → (empty)
keyguard/ci/gitlab.py     → (empty)
keyguard/ci/scan.py       → (empty)
keyguard/ci/output.py     → (empty)
```

- [ ] **Step 2: Verify all existing tests still pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest -q
```

Expected: 103 passed.

- [ ] **Step 3: Commit**

```bash
git add keyguard/ci/
git commit -m "chore: add CI integration package skeleton"
```

---

## Task 2: CiConfig + Load Config Extension

**Files:**
- Modify: `keyguard/config.py`
- Create: `tests/test_ci_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_config.py`:

```python
from pathlib import Path
from keyguard.config import load_config, CiConfig


def test_ci_section_absent_returns_none(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[scan]\npaths = ["."]\n')
    config = load_config(config_path=toml)
    assert config.ci is None


def test_ci_tokens_loaded(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\n'
        'github_token = "ghp_abc"\n'
        'circleci_token = "CCIPAT_xyz"\n'
        'gitlab_token = "glpat-123"\n'
        'max_runs = 5\n'
    )
    config = load_config(config_path=toml)
    assert config.ci is not None
    assert config.ci.github_token == "ghp_abc"
    assert config.ci.circleci_token == "CCIPAT_xyz"
    assert config.ci.gitlab_token == "glpat-123"
    assert config.ci.max_runs == 5


def test_ci_github_orgs_loaded(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\ngithub_token = "ghp_abc"\n'
        '[ci.github]\norgs = ["my-org"]\nrepos = ["my-org/specific"]\n'
    )
    config = load_config(config_path=toml)
    assert config.ci.github_orgs == ["my-org"]
    assert config.ci.github_repos == ["my-org/specific"]


def test_ci_gitlab_custom_url(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\ngitlab_token = "glpat-123"\ngitlab_url = "https://gitlab.mycompany.com"\n'
        '[ci.gitlab]\ngroups = ["my-group"]\n'
    )
    config = load_config(config_path=toml)
    assert config.ci.gitlab_url == "https://gitlab.mycompany.com"
    assert config.ci.gitlab_groups == ["my-group"]


def test_ciconfig_defaults():
    ci = CiConfig()
    assert ci.github_token is None
    assert ci.gitlab_url == "https://gitlab.com"
    assert ci.max_runs == 10
    assert ci.github_orgs == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_config.py -v
```

Expected: `ImportError: cannot import name 'CiConfig'`

- [ ] **Step 3: Add `CiConfig` to `keyguard/config.py` and extend `load_config()`**

Read the current `keyguard/config.py` first, then apply these changes.

At the top of `config.py`, after the existing imports, add the `CiConfig` dataclass **before** the `Config` dataclass:

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

Add `ci: CiConfig | None = None` as the last field of the `Config` dataclass:

```python
@dataclass
class Config:
    paths: list[str] = field(default_factory=lambda: ["."])
    exclude: list[str] = field(default_factory=list)
    scan_git_history: bool = True
    output_formats: list[str] = field(default_factory=lambda: ["terminal"])
    out_file: str | None = None
    redact: bool = True
    slack_webhook: str | None = None
    webhook_url: str | None = None
    disabled_rules: list[str] = field(default_factory=list)
    extra_rules: list[dict] = field(default_factory=list)
    ci: CiConfig | None = None
```

In `load_config()`, after building the existing `Config`, add CI parsing. The full updated function body (replace entirely):

```python
def load_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = Path(".keyguard.toml")

    if not config_path.exists():
        return Config()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid .keyguard.toml: {exc}") from exc

    scan = data.get("scan", {})
    output = data.get("output", {})
    notify = data.get("notify", {})
    rules = data.get("rules", {})
    ci_raw = data.get("ci", {})

    ci_config: CiConfig | None = None
    if ci_raw:
        ci_config = CiConfig(
            github_token=ci_raw.get("github_token"),
            circleci_token=ci_raw.get("circleci_token"),
            gitlab_token=ci_raw.get("gitlab_token"),
            gitlab_url=ci_raw.get("gitlab_url", "https://gitlab.com"),
            max_runs=int(ci_raw.get("max_runs", 10)),
            github_orgs=ci_raw.get("github", {}).get("orgs", []),
            github_repos=ci_raw.get("github", {}).get("repos", []),
            circleci_orgs=ci_raw.get("circleci", {}).get("orgs", []),
            gitlab_groups=ci_raw.get("gitlab", {}).get("groups", []),
            gitlab_repos=ci_raw.get("gitlab", {}).get("repos", []),
        )

    return Config(
        paths=scan.get("paths", ["."]),
        exclude=scan.get("exclude", []),
        scan_git_history=scan.get("scan_git_history", True),
        output_formats=output.get("format", ["terminal"]),
        redact=output.get("redact", True),
        slack_webhook=notify.get("slack_webhook"),
        webhook_url=notify.get("webhook_url"),
        disabled_rules=rules.get("disabled", []),
        extra_rules=rules.get("extra", []),
        ci=ci_config,
    )
```

- [ ] **Step 4: Run all config tests**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_config.py tests/test_config.py -v
```

Expected: all 11 tests pass (5 new + 6 existing).

- [ ] **Step 5: Commit**

```bash
git add keyguard/config.py tests/test_ci_config.py
git commit -m "feat: add CiConfig dataclass and CI config parsing"
```

---

## Task 3: CiChunk + CiFinding Models

**Files:**
- Modify: `keyguard/ci/models.py`
- Create: `tests/test_ci_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_models.py`:

```python
from keyguard.ci.models import CiChunk, CiFinding


def test_ci_chunk_fields():
    chunk = CiChunk(
        text="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        platform="github",
        repo="my-org/api-service",
        source_type="log",
        source_id="run:123/job:456",
    )
    assert chunk.platform == "github"
    assert chunk.source_type == "log"
    assert chunk.is_name_only is False


def test_ci_chunk_name_only_flag():
    chunk = CiChunk(
        text="GOOGLE_API_KEY",
        platform="circleci",
        repo="my-org/api-service",
        source_type="variable",
        source_id="GOOGLE_API_KEY",
        is_name_only=True,
    )
    assert chunk.is_name_only is True


def test_ci_finding_to_dict_redacts():
    f = CiFinding(
        platform="github",
        repo="my-org/api-service",
        source_type="log",
        source_id="run:123/job:456",
        rule_id="google-api-key",
        severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87,
        line=42,
    )
    d = f.to_dict(redact=True)
    assert d["matched_value"] == "[REDACTED]"
    assert d["platform"] == "github"
    assert d["repo"] == "my-org/api-service"


def test_ci_finding_to_dict_unredacted():
    f = CiFinding(
        platform="github", repo="org/repo", source_type="variable",
        source_id="MAPS_KEY", rule_id="google-api-key", severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87, line=1,
    )
    d = f.to_dict(redact=False)
    assert "AIzaSy" in d["matched_value"]


def test_ci_finding_to_dict_all_keys():
    f = CiFinding(
        platform="github", repo="org/repo", source_type="log",
        source_id="run:1", rule_id="google-api-key", severity="critical",
        matched_value="x", entropy=4.5, line=1,
    )
    assert set(f.to_dict().keys()) == {
        "platform", "repo", "source_type", "source_id",
        "rule_id", "severity", "matched_value", "entropy", "line",
    }
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_models.py -v
```

Expected: `ImportError: cannot import name 'CiChunk'`

- [ ] **Step 3: Implement `keyguard/ci/models.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CiChunk:
    text: str
    platform: str       # "github" | "circleci" | "gitlab"
    repo: str           # "owner/name"
    source_type: str    # "log" | "variable"
    source_id: str      # run/job ID for logs; variable name for variables
    is_name_only: bool = False  # True for CircleCI masked variable name checks


@dataclass
class CiFinding:
    platform: str
    repo: str
    source_type: str    # "log" | "variable"
    source_id: str
    rule_id: str
    severity: str       # "critical" | "high" | "info"
    matched_value: str
    entropy: float
    line: int

    def to_dict(self, redact: bool = True) -> dict:
        value = "[REDACTED]" if redact else self.matched_value
        return {
            "platform": self.platform,
            "repo": self.repo,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "matched_value": value,
            "entropy": round(self.entropy, 4),
            "line": self.line,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_models.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/models.py tests/test_ci_models.py
git commit -m "feat: add CiChunk and CiFinding dataclasses"
```

---

## Task 4: GitHubCiScanner

**Files:**
- Modify: `keyguard/ci/github.py`
- Create: `tests/test_ci_github.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_github.py`:

```python
from unittest.mock import MagicMock, patch
from keyguard.ci.github import GitHubCiScanner
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig


def _config(**kwargs) -> CiConfig:
    defaults = dict(github_token="ghp_test", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
    else:
        r.json.return_value = data
    r.headers = {}
    return r


@patch("keyguard.ci.github.requests.Session")
def test_scans_variables(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, {"variables": [
            {"name": "MAPS_KEY", "value": "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"},
        ]}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_repos=["my-org/api-service"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    variable_chunks = [c for c in chunks if c.source_type == "variable"]
    assert len(variable_chunks) == 1
    assert variable_chunks[0].text == "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"
    assert variable_chunks[0].platform == "github"
    assert variable_chunks[0].repo == "my-org/api-service"
    assert variable_chunks[0].source_id == "MAPS_KEY"


@patch("keyguard.ci.github.requests.Session")
def test_scans_job_logs(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, {"variables": []}),
        _resp(200, {"workflow_runs": [{"id": 111}]}),
        _resp(200, {"jobs": [{"id": 999}]}),
        _resp(200, "log line with AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X here"),
    ]
    cfg = _config(github_repos=["my-org/api-service"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text
    assert log_chunks[0].source_id == "run:111/job:999"


@patch("keyguard.ci.github.requests.Session")
def test_403_on_variables_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(403, {}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_repos=["my-org/private-repo"])
    scanner = GitHubCiScanner(cfg)
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err


@patch("keyguard.ci.github.requests.Session")
def test_org_repos_listed(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"full_name": "my-org/repo-a"}]),
        _resp(200, {"variables": []}),
        _resp(200, {"workflow_runs": []}),
    ]
    cfg = _config(github_orgs=["my-org"])
    scanner = GitHubCiScanner(cfg)
    list(scanner.scan())
    assert session.get.call_count >= 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_github.py -v
```

Expected: `ImportError: cannot import name 'GitHubCiScanner'`

- [ ] **Step 3: Implement `keyguard/ci/github.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_github.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/github.py tests/test_ci_github.py
git commit -m "feat: add GitHubCiScanner for variables and job logs"
```

---

## Task 5: CircleCiScanner

**Files:**
- Modify: `keyguard/ci/circleci.py`
- Create: `tests/test_ci_circleci.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_circleci.py`:

```python
import re
from unittest.mock import MagicMock, patch
from keyguard.ci.circleci import CircleCiScanner
from keyguard.config import CiConfig

_SUSPICIOUS = re.compile(r"(GOOGLE|GEMINI|GCP|FIREBASE|GCLOUD|VERTEX)", re.IGNORECASE)


def _config(**kwargs) -> CiConfig:
    defaults = dict(circleci_token="CCIPAT_test", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
    else:
        r.json.return_value = data
    return r


@patch("keyguard.ci.circleci.requests.Session")
def test_suspicious_variable_name_yields_name_only_chunk(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"name": "GOOGLE_API_KEY", "value": "xxxxxx"},
                    {"name": "DB_HOST", "value": "xxxxxx"}]),
        _resp(200, {"items": []}),
    ]
    cfg = _config(circleci_orgs=["my-org"])
    # Patch org repo discovery
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    name_chunks = [c for c in chunks if c.is_name_only]
    assert len(name_chunks) == 1
    assert name_chunks[0].text == "GOOGLE_API_KEY"
    assert name_chunks[0].source_id == "GOOGLE_API_KEY"


@patch("keyguard.ci.circleci.requests.Session")
def test_non_suspicious_variable_not_yielded(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"name": "DB_HOST", "value": "xxxxxx"}]),
        _resp(200, {"items": []}),
    ]
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    assert not any(c.is_name_only for c in chunks)


@patch("keyguard.ci.circleci.requests.Session")
def test_log_scanning_yields_log_chunk(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, []),
        _resp(200, {"items": [{"id": "pipe-1", "number": 42}]}),
        _resp(200, {"items": [{"id": "wf-1"}]}),
        _resp(200, {"items": [{"id": 99, "job_number": 42}]}),
        _resp(200, "step output: AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"),
    ]
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text


@patch("keyguard.ci.circleci.requests.Session")
def test_401_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _resp(401, {})
    cfg = _config()
    scanner = CircleCiScanner(cfg, repos_override=["github/my-org/api-service"])
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_circleci.py -v
```

Expected: `ImportError: cannot import name 'CircleCiScanner'`

- [ ] **Step 3: Implement `keyguard/ci/circleci.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_circleci.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/circleci.py tests/test_ci_circleci.py
git commit -m "feat: add CircleCiScanner for variable names and job logs"
```

---

## Task 6: GitLabCiScanner

**Files:**
- Modify: `keyguard/ci/gitlab.py`
- Create: `tests/test_ci_gitlab.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_gitlab.py`:

```python
from unittest.mock import MagicMock, patch
from keyguard.ci.gitlab import GitLabCiScanner
from keyguard.config import CiConfig


def _config(**kwargs) -> CiConfig:
    defaults = dict(gitlab_token="glpat-test", gitlab_url="https://gitlab.com", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _resp(status: int, data, headers: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if isinstance(data, str):
        r.text = data
    else:
        r.json.return_value = data
    r.headers = headers or {}
    return r


@patch("keyguard.ci.gitlab.requests.Session")
def test_scans_variables(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, [{"key": "MAPS_KEY", "value": "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"}]),
        _resp(200, []),
    ]
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/api-service"}])
    chunks = list(scanner.scan())
    variable_chunks = [c for c in chunks if c.source_type == "variable"]
    assert len(variable_chunks) == 1
    assert variable_chunks[0].text == "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"
    assert variable_chunks[0].source_id == "MAPS_KEY"


@patch("keyguard.ci.gitlab.requests.Session")
def test_scans_pipeline_job_logs(mock_session_cls):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.side_effect = [
        _resp(200, []),
        _resp(200, [{"id": 55}]),
        _resp(200, [{"id": 99}]),
        _resp(200, "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X found in log"),
    ]
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/api-service"}])
    chunks = list(scanner.scan())
    log_chunks = [c for c in chunks if c.source_type == "log"]
    assert len(log_chunks) == 1
    assert "AIzaSy" in log_chunks[0].text


@patch("keyguard.ci.gitlab.requests.Session")
def test_403_skips_gracefully(mock_session_cls, capsys):
    session = MagicMock()
    mock_session_cls.return_value = session
    session.get.return_value = _resp(403, {})
    cfg = _config()
    scanner = GitLabCiScanner(cfg, repos_override=[{"id": 42, "path_with_namespace": "my-group/repo"}])
    chunks = list(scanner.scan())
    assert chunks == []
    assert "Warning" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_gitlab.py -v
```

Expected: `ImportError: cannot import name 'GitLabCiScanner'`

- [ ] **Step 3: Implement `keyguard/ci/gitlab.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_gitlab.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/gitlab.py tests/test_ci_gitlab.py
git commit -m "feat: add GitLabCiScanner for variables and pipeline logs"
```

---

## Task 7: ci_scan() Orchestration

**Files:**
- Modify: `keyguard/ci/scan.py`
- Create: `tests/test_ci_scan.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_scan.py`:

```python
from unittest.mock import MagicMock, patch
from keyguard.ci.scan import ci_scan
from keyguard.ci.models import CiChunk
from keyguard.config import CiConfig


def _config(**kwargs) -> CiConfig:
    defaults = dict(github_token="ghp_test", max_runs=2)
    defaults.update(kwargs)
    return CiConfig(**defaults)


def _make_chunk(text: str, platform: str = "github", is_name_only: bool = False) -> CiChunk:
    return CiChunk(
        text=text,
        platform=platform,
        repo="org/repo",
        source_type="variable" if is_name_only else "log",
        source_id="LOG_SRC",
        is_name_only=is_name_only,
    )


@patch("keyguard.ci.scan.GitHubCiScanner")
def test_credential_in_chunk_produces_finding(mock_gh_cls):
    scanner = MagicMock()
    mock_gh_cls.return_value = scanner
    scanner.scan.return_value = iter([
        _make_chunk('KEY = "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X"')
    ])
    findings = ci_scan(_config())
    assert len(findings) == 1
    assert findings[0].rule_id == "google-api-key"
    assert findings[0].platform == "github"
    assert findings[0].repo == "org/repo"


@patch("keyguard.ci.scan.GitHubCiScanner")
def test_clean_chunk_produces_no_findings(mock_gh_cls):
    scanner = MagicMock()
    mock_gh_cls.return_value = scanner
    scanner.scan.return_value = iter([_make_chunk("print('hello world')")])
    assert ci_scan(_config()) == []


@patch("keyguard.ci.scan.GitHubCiScanner")
def test_name_only_chunk_produces_info_finding(mock_gh_cls):
    scanner = MagicMock()
    mock_gh_cls.return_value = scanner
    scanner.scan.return_value = iter([
        _make_chunk("GOOGLE_API_KEY", is_name_only=True)
    ])
    findings = ci_scan(_config())
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert findings[0].rule_id == "masked-variable-name"


@patch("keyguard.ci.scan.CircleCiScanner")
@patch("keyguard.ci.scan.GitHubCiScanner")
def test_platform_filter_skips_other_platforms(mock_gh_cls, mock_cci_cls):
    mock_gh_cls.return_value.scan.return_value = iter([])
    mock_cci_cls.return_value.scan.return_value = iter([])
    ci_scan(_config(circleci_token="CCIPAT_x"), platform="github")
    mock_cci_cls.assert_not_called()


@patch("keyguard.ci.scan.GitHubCiScanner")
def test_repos_override_passed_to_scanner(mock_gh_cls):
    scanner = MagicMock()
    mock_gh_cls.return_value = scanner
    scanner.scan.return_value = iter([])
    ci_scan(_config(), repos=["my-org/specific"])
    mock_gh_cls.assert_called_once_with(_config(), repos_override=["my-org/specific"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_scan.py -v
```

Expected: `ImportError: cannot import name 'ci_scan'`

- [ ] **Step 3: Implement `keyguard/ci/scan.py`**

```python
from __future__ import annotations
from keyguard.ci.models import CiChunk, CiFinding
from keyguard.ci.github import GitHubCiScanner
from keyguard.ci.circleci import CircleCiScanner
from keyguard.ci.gitlab import GitLabCiScanner
from keyguard.config import CiConfig
from keyguard.engine.rules import RuleLoader
from keyguard.engine.matcher import RegexMatcher
from keyguard.models import Chunk


def ci_scan(
    ci_config: CiConfig,
    platform: str | None = None,
    repos: list[str] | None = None,
) -> list[CiFinding]:
    rules = RuleLoader.load_builtin(
        disabled=[], extra_rules=[]
    )
    matcher = RegexMatcher(rules)
    findings: list[CiFinding] = []

    scanners = []
    if (platform is None or platform == "github") and ci_config.github_token:
        scanners.append(GitHubCiScanner(ci_config, repos_override=repos))
    if (platform is None or platform == "circleci") and ci_config.circleci_token:
        scanners.append(CircleCiScanner(ci_config, repos_override=repos))
    if (platform is None or platform == "gitlab") and ci_config.gitlab_token:
        scanners.append(GitLabCiScanner(ci_config, repos_override=repos))

    for scanner in scanners:
        for ci_chunk in scanner.scan():
            if ci_chunk.is_name_only:
                findings.append(CiFinding(
                    platform=ci_chunk.platform,
                    repo=ci_chunk.repo,
                    source_type="variable",
                    source_id=ci_chunk.source_id,
                    rule_id="masked-variable-name",
                    severity="info",
                    matched_value=f"[masked: {ci_chunk.text}]",
                    entropy=0.0,
                    line=0,
                ))
            else:
                chunk = Chunk(
                    text=ci_chunk.text,
                    file_path=ci_chunk.source_id,
                    line_offset=1,
                )
                for finding in matcher.scan(chunk):
                    findings.append(CiFinding(
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

    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_scan.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/scan.py tests/test_ci_scan.py
git commit -m "feat: add ci_scan() orchestration with name-only finding support"
```

---

## Task 8: CiTerminalReporter + CiJsonExporter

**Files:**
- Modify: `keyguard/ci/output.py`
- Create: `tests/test_ci_output.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_output.py`:

```python
import json
from io import StringIO
from rich.console import Console
from keyguard.ci.models import CiFinding
from keyguard.ci.output import CiTerminalReporter, CiJsonExporter


def _finding(**kwargs) -> CiFinding:
    defaults = dict(
        platform="github", repo="my-org/api-service",
        source_type="log", source_id="run:1/job:2",
        rule_id="google-api-key", severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87, line=42,
    )
    defaults.update(kwargs)
    return CiFinding(**defaults)


def _capture(findings, redact=True) -> str:
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    CiTerminalReporter(console=console, redact=redact).report(findings)
    return buf.getvalue()


def test_terminal_shows_platform_and_repo():
    output = _capture([_finding()])
    assert "github" in output
    assert "my-org/api-service" in output


def test_terminal_shows_rule_id():
    assert "google-api-key" in _capture([_finding()])


def test_terminal_redacts_value():
    output = _capture([_finding()], redact=True)
    assert "AIzaSy" not in output
    assert "[REDACTED]" in output


def test_terminal_no_findings_clean():
    output = _capture([])
    assert "No CI findings" in output


def test_terminal_shows_count():
    output = _capture([_finding(), _finding(severity="high")])
    assert "2" in output


def test_json_exporter_writes_valid_json(tmp_path):
    out = tmp_path / "ci.json"
    CiJsonExporter(out_file=str(out)).report([_finding()])
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["platform"] == "github"
    assert data[0]["matched_value"] == "[REDACTED]"


def test_json_exporter_empty_writes_empty_list(tmp_path):
    out = tmp_path / "ci.json"
    CiJsonExporter(out_file=str(out)).report([])
    assert json.loads(out.read_text()) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_output.py -v
```

Expected: `ImportError: cannot import name 'CiTerminalReporter'`

- [ ] **Step 3: Implement `keyguard/ci/output.py`**

```python
from __future__ import annotations
import json
from rich.console import Console
from rich.table import Table
from rich import box
from keyguard.ci.models import CiFinding

_SEVERITY_COLORS = {"critical": "bold red", "high": "red", "info": "blue"}


class CiTerminalReporter:
    def __init__(self, console: Console | None = None, redact: bool = True) -> None:
        self._console = console or Console()
        self._redact = redact

    def report(self, findings: list[CiFinding]) -> None:
        if not findings:
            self._console.print("[green]No CI findings detected.[/green]")
            return

        by_platform: dict[str, list[CiFinding]] = {}
        for f in findings:
            by_platform.setdefault(f.platform, []).append(f)

        for platform, pfindings in by_platform.items():
            self._console.print(f"\nPlatform: {platform.capitalize()}")
            by_repo: dict[str, list[CiFinding]] = {}
            for f in pfindings:
                by_repo.setdefault(f.repo, []).append(f)

            for repo, rfindings in by_repo.items():
                self._console.print(f"  Repo: {repo}")
                table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                table.add_column("Severity")
                table.add_column("Type")
                table.add_column("Source")
                table.add_column("Value")

                for f in rfindings:
                    color = _SEVERITY_COLORS.get(f.severity, "white")
                    value = "[REDACTED]" if self._redact else f.matched_value
                    table.add_row(
                        f"[{color}]{f.severity.upper()}[/{color}]",
                        f.source_type,
                        f.source_id,
                        value,
                    )
                self._console.print(table)

        critical = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        info = sum(1 for f in findings if f.severity == "info")
        self._console.print(
            f"Found {len(findings)} finding(s). "
            f"Critical: {critical}, High: {high}, Info: {info}."
        )


class CiJsonExporter:
    def __init__(self, out_file: str, redact: bool = True) -> None:
        self._out_file = out_file
        self._redact = redact

    def report(self, findings: list[CiFinding]) -> None:
        with open(self._out_file, "w") as fh:
            json.dump([f.to_dict(redact=self._redact) for f in findings], fh, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_output.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add keyguard/ci/output.py tests/test_ci_output.py
git commit -m "feat: add CiTerminalReporter and CiJsonExporter"
```

---

## Task 9: CLI ci Command

**Files:**
- Modify: `keyguard/cli.py`
- Create: `tests/test_ci_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ci_cli.py`:

```python
from unittest.mock import patch
from click.testing import CliRunner
from keyguard.cli import main
from keyguard.ci.models import CiFinding


def _finding(**kwargs) -> CiFinding:
    defaults = dict(
        platform="github", repo="org/repo", source_type="log",
        source_id="run:1", rule_id="google-api-key", severity="critical",
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87, line=1,
    )
    defaults.update(kwargs)
    return CiFinding(**defaults)


def _toml_with_ci(tmp_path) -> str:
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[ci]\ngithub_token = "ghp_test"\n')
    return str(toml)


@patch("keyguard.cli.ci_scan")
def test_ci_no_findings_exits_zero(mock_scan, tmp_path):
    mock_scan.return_value = []
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert result.exit_code == 0


@patch("keyguard.cli.ci_scan")
def test_ci_with_findings_exits_one(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert result.exit_code == 1


@patch("keyguard.cli.ci_scan")
def test_ci_output_contains_platform(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    result = CliRunner().invoke(main, ["ci", "--config", _toml_with_ci(tmp_path)])
    assert "github" in result.output.lower()


def test_ci_no_tokens_exits_two(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[scan]\npaths = ["."]\n')
    result = CliRunner().invoke(main, ["ci", "--config", str(toml)])
    assert result.exit_code == 2


@patch("keyguard.cli.ci_scan")
def test_ci_platform_flag_passed(mock_scan, tmp_path):
    mock_scan.return_value = []
    CliRunner().invoke(main, ["ci", "--platform", "github", "--config", _toml_with_ci(tmp_path)])
    _, kwargs = mock_scan.call_args
    assert kwargs["platform"] == "github"


@patch("keyguard.cli.ci_scan")
def test_ci_json_output_writes_file(mock_scan, tmp_path):
    mock_scan.return_value = [_finding()]
    out = tmp_path / "ci.json"
    CliRunner().invoke(
        main, ["ci", "--output", "json", "--out-file", str(out), "--config", _toml_with_ci(tmp_path)]
    )
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data[0]["platform"] == "github"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_cli.py -v
```

Expected: `No such command 'ci'` or import error.

- [ ] **Step 3: Add module-level CI imports to `keyguard/cli.py`**

After the existing auditor imports at the top of `keyguard/cli.py`, add:

```python
from keyguard.ci.scan import ci_scan
from keyguard.ci.output import CiTerminalReporter, CiJsonExporter
```

- [ ] **Step 4: Append `ci` command to `keyguard/cli.py`** (after the `audit` command):

```python
@main.command()
@click.option(
    "--platform", default=None,
    type=click.Choice(["github", "circleci", "gitlab"]),
    help="Scan only this platform.",
)
@click.option(
    "--repo", "repos", multiple=True,
    help="Narrow scan to specific repo (repeatable).",
)
@click.option(
    "--output", "output_formats", multiple=True,
    type=click.Choice(["json"]),
    help="Additional output format. Terminal is always on.",
)
@click.option("--out-file", default=None, help="Path for JSON output file.")
@click.option("--config", "config_path", default=".keyguard.toml",
              help="Path to .keyguard.toml config file.")
def ci(platform, repos, output_formats, out_file, config_path) -> None:
    """Scan CI platforms for exposed credentials in logs and variables."""
    try:
        config = load_config(
            config_path=config_path if config_path != ".keyguard.toml" else None
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if config.ci is None:
        click.echo(
            "Error: No CI tokens configured in [ci] section of .keyguard.toml",
            err=True,
        )
        sys.exit(2)

    findings = ci_scan(
        ci_config=config.ci,
        platform=platform,
        repos=list(repos) if repos else None,
    )

    CiTerminalReporter(redact=config.redact).report(findings)

    if "json" in output_formats and out_file:
        CiJsonExporter(out_file=out_file, redact=config.redact).report(findings)

    sys.exit(1 if findings else 0)
```

- [ ] **Step 5: Run all CI CLI tests**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest tests/test_ci_cli.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 6: Run full test suite**

```bash
/Users/arzaan.mairaj/PycharmProjects/PythonProject3/.venv/bin/pytest -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 7: Commit and push**

```bash
git add keyguard/cli.py tests/test_ci_cli.py
git commit -m "feat: add keyguard ci CLI command for CI platform credential scanning"
git push
```

---

## Self-Review

**Spec coverage:**
- GitHub Actions variables + logs ✓ Task 4
- CircleCI masked variable name detection + logs ✓ Task 5
- GitLab variables + logs ✓ Task 6
- `CiConfig` with all fields + `load_config()` extension ✓ Task 2
- `CiChunk` with `is_name_only` flag ✓ Task 3
- `CiFinding` with `to_dict(redact)` ✓ Task 3
- `ci_scan()` with platform filter, repo override, name-only detection ✓ Task 7
- `CiTerminalReporter` grouped by platform+repo ✓ Task 8
- `CiJsonExporter` ✓ Task 8
- `keyguard ci` CLI with `--platform`, `--repo`, `--output`, `--out-file`, `--config` ✓ Task 9
- Exit codes 0/1/2 ✓ Task 9
- No tokens → exit 2 ✓ Task 9
- 403/404 per repo → warning, skip ✓ Tasks 4/5/6
- `.keyguard.toml` [ci] example ✓ covered in spec, parseable via Task 2
- No new dependencies ✓ (uses existing `requests`)
