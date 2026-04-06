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
