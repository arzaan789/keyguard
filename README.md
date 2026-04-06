# keyguard

Scan codebases, GCP projects, and CI pipelines for exposed Google API credentials — before they get exploited.

**The problem:** Google retroactively enabled Gemini API access on existing API keys (Maps, Places, etc.) that were designed to be public and embedded in client-side code. When someone on your team enables Gemini in the same GCP project, those already-public keys silently become Gemini credentials — exposing your project to unauthorized AI usage and $80k+ billing incidents ([context](https://news.ycombinator.com/item?id=47156925)).

**What keyguard does:**
- `keyguard scan` — finds credential strings in source files and git history using regex + entropy detection
- `keyguard audit` — connects to live GCP projects and flags API keys that have Gemini access right now
- `keyguard ci` — scans GitHub Actions, CircleCI, and GitLab CI logs and variables for leaked credentials

---

## Install

```bash
pip install keyguard-scan
```

Or clone and install in development mode:

```bash
git clone https://github.com/arzaan789/keyguard.git
cd keyguard
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Scan current directory and git history
keyguard scan .

# Audit your live GCP projects
keyguard audit

# Scan CI platforms
keyguard ci
```

---

## Commands

### `keyguard scan`

Scans source files and git history for exposed credentials using regex + Shannon entropy filtering. Low-entropy placeholders like `"REPLACE_ME"` or `"XXXXXXXX"` are automatically ignored.

```bash
# Scan a directory (files + full git history)
keyguard scan .

# Files only, skip git history
keyguard scan . --no-git-history

# Export to JSON and SARIF
keyguard scan . --output json --output sarif --out-file report

# Show actual key values (not redacted)
keyguard scan . --no-redact

# Use a custom config file
keyguard scan . --config /path/to/.keyguard.toml
```

**Exit codes:** `0` = clean, `1` = findings, `2` = error

### `keyguard audit`

Connects to live GCP projects via the Cloud Resource Manager, Service Usage, and API Keys APIs. Flags keys that are unrestricted (silent Gemini access) or that explicitly allow `generativelanguage.googleapis.com` while Gemini is enabled on the project.

Authentication uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) by default — run `gcloud auth application-default login` first.

```bash
# Audit all accessible GCP projects
keyguard audit

# Audit specific project(s)
keyguard audit --project my-project-id --project another-project

# Use a service account key file
keyguard audit --gcp-credentials /path/to/key.json

# Export JSON findings
keyguard audit --output json --out-file gcp-findings.json
```

**Findings:**
- `CRITICAL` — key has no API restrictions + Gemini is enabled (the silent Maps→Gemini upgrade scenario)
- `HIGH` — key explicitly allows `generativelanguage.googleapis.com` (intentional but potentially embedded in client code)

### `keyguard ci`

Scans CI platform logs and stored variables for exposed credentials. Supports GitHub Actions, CircleCI, and GitLab CI.

```bash
# Scan all configured platforms
keyguard ci

# Scan one platform only
keyguard ci --platform github

# Narrow to a specific repo
keyguard ci --repo my-org/api-service

# Export JSON findings
keyguard ci --output json --out-file ci-findings.json
```

**What it scans:**
- **GitHub Actions** — plaintext repository variables + workflow run job logs
- **CircleCI** — environment variable names (values are masked by CircleCI) + pipeline job step logs
- **GitLab CI** — project variables (plaintext) + pipeline job traces

### `keyguard watch`

Re-scans files on every change. Useful during development.

```bash
keyguard watch .
```

### `keyguard rules list`

Lists all active detection rules.

```bash
keyguard rules list
```

### `keyguard config check`

Validates a `.keyguard.toml` configuration file.

```bash
keyguard config check
keyguard config check --config /path/to/.keyguard.toml
```

---

## Configuration

Create a `.keyguard.toml` in your project root:

```toml
[scan]
paths = ["."]
exclude = ["tests/fixtures/", "**/*.example"]
scan_git_history = true

[output]
format = ["terminal", "json"]
redact = true

[notify]
slack_webhook = "https://hooks.slack.com/services/..."

[rules]
disabled = []

# CI platform authentication and scope
[ci]
github_token    = "ghp_xxxxxxxxxxxxxxxxxxxx"
circleci_token  = "CCIPAT_xxxxxxxxxxxxxxxx"
gitlab_token    = "glpat-xxxxxxxxxxxxxxxxxxxx"
gitlab_url      = "https://gitlab.com"   # override for self-hosted GitLab
max_runs        = 10                     # recent runs/pipelines per repo

[ci.github]
orgs  = ["my-org"]
repos = ["my-org/specific-repo"]         # optional: scan specific repos only

[ci.circleci]
orgs = ["my-org"]

[ci.gitlab]
groups = ["my-group"]
```

---

## Detection

Keyguard uses a **regex + Shannon entropy** approach. Each rule defines:
- A pattern that matches the credential's structure (e.g., `AIza[0-9A-Za-z\-_]{35}` for Google API keys)
- A minimum entropy threshold that filters out low-entropy placeholders

Built-in rules detect:
| Rule ID | What it finds |
|---|---|
| `google-api-key` | Google API keys (`AIza...`) — including Maps keys silently granted Gemini access |
| `gcp-service-account-key` | GCP service account RSA private keys |
| `google-oauth-client-secret` | Google OAuth2 client secrets (`GOCSPX-...`) |

You can add custom rules in `.keyguard.toml`:

```toml
[[rules.extra]]
id = "my-internal-token"
description = "Internal service token"
pattern = "tok-[0-9a-f]{32}"
entropy_min = 3.5
severity = "high"
tags = ["internal"]
```

---

## CI Integration

### GitHub Actions

```yaml
name: keyguard scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # full history for git scan
      - run: pip install keyguard-scan
      - run: keyguard scan .
```

### Pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: keyguard
        name: keyguard credential scan
        entry: keyguard scan --no-git-history
        language: system
        pass_filenames: false
```

### Docker

```bash
docker run --rm -v $(pwd):/repo ghcr.io/arzaan789/keyguard scan /repo
```

---

## Output Formats

**Terminal** (default) — colored table grouped by severity.

**JSON** — machine-readable findings array:
```bash
keyguard scan . --output json --out-file findings.json
```

**SARIF** — integrates with GitHub's Security tab and other SAST tools:
```bash
keyguard scan . --output sarif --out-file findings.sarif
```

**Slack webhook** — posts a summary when findings are detected:
```toml
[notify]
slack_webhook = "https://hooks.slack.com/services/..."
```

---

## Development

```bash
git clone https://github.com/arzaan789/keyguard.git
cd keyguard
pip install -e ".[dev]"
pytest
```

**143 tests, 0 failures.**

Project structure:
```
keyguard/
  scanner/      # file + git history scanners
  engine/       # regex + entropy detection (rules, matcher)
  output/       # terminal, JSON/SARIF, webhook
  auditor/      # GCP API client + audit logic
  ci/           # GitHub Actions, CircleCI, GitLab CI scanners
  cli.py        # Click CLI entry point
  config.py     # .keyguard.toml loader
```

---

## Roadmap

- [x] v1 — File scanner (source code + git history)
- [x] v2 — GCP API auditor (live project audit via GCP APIs)
- [x] v3 — CI platform integration (GitHub Actions, CircleCI, GitLab CI)

---

## License

MIT
