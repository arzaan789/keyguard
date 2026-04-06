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
