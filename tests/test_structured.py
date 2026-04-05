import json
from pathlib import Path
from keyguard.output.structured import JsonExporter, SarifExporter
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


def test_json_exporter_writes_valid_json(tmp_path):
    out = tmp_path / "report.json"
    exporter = JsonExporter(out_file=str(out), redact=True)
    exporter.report([_make_finding()])
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert data[0]["rule_id"] == "google-api-key"


def test_json_exporter_redacts(tmp_path):
    out = tmp_path / "report.json"
    exporter = JsonExporter(out_file=str(out), redact=True)
    exporter.report([_make_finding()])
    data = json.loads(out.read_text())
    assert data[0]["matched_value"] == "[REDACTED]"


def test_json_exporter_no_findings_writes_empty_list(tmp_path):
    out = tmp_path / "report.json"
    exporter = JsonExporter(out_file=str(out), redact=True)
    exporter.report([])
    data = json.loads(out.read_text())
    assert data == []


def test_sarif_exporter_writes_valid_sarif(tmp_path):
    out = tmp_path / "report.sarif"
    exporter = SarifExporter(out_file=str(out), redact=True)
    exporter.report([_make_finding()])
    data = json.loads(out.read_text())
    assert data["version"] == "2.1.0"
    assert "runs" in data
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "google-api-key"


def test_sarif_location_has_uri_and_line(tmp_path):
    out = tmp_path / "report.sarif"
    exporter = SarifExporter(out_file=str(out), redact=True)
    exporter.report([_make_finding(file_path="src/app.py", line=42)])
    data = json.loads(out.read_text())
    location = data["runs"][0]["results"][0]["locations"][0]
    assert location["physicalLocation"]["artifactLocation"]["uri"] == "src/app.py"
    assert location["physicalLocation"]["region"]["startLine"] == 42


def test_sarif_severity_mapping(tmp_path):
    out = tmp_path / "report.sarif"
    exporter = SarifExporter(out_file=str(out), redact=True)
    exporter.report([_make_finding(severity="medium")])
    data = json.loads(out.read_text())
    assert data["runs"][0]["results"][0]["level"] == "warning"
