from io import StringIO
from rich.console import Console
from keyguard.output.terminal import TerminalReporter
from keyguard.models import Finding


def _make_finding(**kwargs) -> Finding:
    defaults = dict(
        rule_id="google-api-key",
        description="Google API Key",
        severity="critical",
        file_path="src/app.py",
        line=42,
        matched_value="AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X",
        entropy=4.87,
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def _capture_report(findings, redact=True) -> str:
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False)
    reporter = TerminalReporter(redact=redact, console=console)
    reporter.report(findings)
    return buf.getvalue()


def test_reports_finding_with_file_and_line():
    output = _capture_report([_make_finding()])
    assert "src/app.py" in output
    assert "42" in output


def test_reports_rule_id():
    output = _capture_report([_make_finding()])
    assert "google-api-key" in output


def test_redacts_matched_value():
    output = _capture_report([_make_finding()], redact=True)
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X" not in output
    assert "[REDACTED]" in output


def test_shows_unredacted_when_disabled():
    output = _capture_report([_make_finding()], redact=False)
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0KLmnopqrst12X" in output


def test_shows_commit_when_present():
    finding = _make_finding(commit="a3f9c12", author="dev@example.com")
    output = _capture_report([finding])
    assert "a3f9c12" in output


def test_summary_shows_count():
    findings = [_make_finding(), _make_finding(severity="high")]
    output = _capture_report(findings)
    assert "2" in output


def test_no_findings_shows_clean():
    output = _capture_report([])
    assert "No findings" in output or "clean" in output.lower() or "0" in output
