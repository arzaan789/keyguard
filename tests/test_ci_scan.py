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
