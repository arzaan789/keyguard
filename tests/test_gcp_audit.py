from unittest.mock import MagicMock
from keyguard.auditor.audit import GcpFinding, audit_projects


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


def _make_client(projects=None, gemini_states=None, keys_by_project=None) -> MagicMock:
    client = MagicMock()
    client.list_projects.return_value = projects or []
    client.gemini_enabled.side_effect = lambda pid: (gemini_states or {}).get(pid, False)
    client.list_keys.side_effect = lambda pid: (keys_by_project or {}).get(pid, [])
    return client


def _unrestricted_key(display_name: str = "Maps Key") -> dict:
    return {
        "name": "projects/123/locations/global/keys/abc",
        "displayName": display_name,
        "restrictions": None,
    }


def _gemini_key(display_name: str = "Gemini Key") -> dict:
    return {
        "name": "projects/123/locations/global/keys/xyz",
        "displayName": display_name,
        "restrictions": {
            "apiTargets": [{"service": "generativelanguage.googleapis.com"}]
        },
    }


def _maps_only_key() -> dict:
    return {
        "name": "projects/123/locations/global/keys/maps",
        "displayName": "Maps Only",
        "restrictions": {
            "apiTargets": [{"service": "maps-backend.googleapis.com"}]
        },
    }


def test_unrestricted_key_gemini_enabled_is_critical():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].restriction == "none"
    assert findings[0].project_id == "proj-a"
    assert findings[0].key_display_name == "Maps Key"


def test_gemini_explicit_key_is_high():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_gemini_key()]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].restriction == "gemini_explicit"


def test_maps_only_key_not_flagged():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_maps_only_key()]},
    )
    assert audit_projects(client) == []


def test_gemini_disabled_no_findings():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": False},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    assert audit_projects(client) == []


def test_specific_project_ids_skips_discovery():
    client = _make_client(
        gemini_states={"specific-proj": True},
        keys_by_project={"specific-proj": [_unrestricted_key()]},
    )
    findings = audit_projects(client, project_ids=["specific-proj"])
    client.list_projects.assert_not_called()
    assert len(findings) == 1
    assert findings[0].project_id == "specific-proj"


def test_empty_restrictions_dict_treated_as_unrestricted():
    key = {
        "name": "projects/123/locations/global/keys/abc",
        "displayName": "Empty Restrict Key",
        "restrictions": {},
    }
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [key]},
    )
    findings = audit_projects(client)
    assert len(findings) == 1
    assert findings[0].restriction == "none"


def test_key_id_extracted_from_resource_name():
    client = _make_client(
        projects=[{"projectId": "proj-a", "name": "Project A"}],
        gemini_states={"proj-a": True},
        keys_by_project={"proj-a": [_unrestricted_key()]},
    )
    findings = audit_projects(client)
    assert findings[0].key_id == "abc"
