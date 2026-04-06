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
    output = _capture([
        _make_finding(),
        _make_finding(severity="high", restriction="gemini_explicit"),
    ])
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
