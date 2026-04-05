import responses as responses_lib
import requests
import pytest
from keyguard.output.webhook import WebhookNotifier
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


@responses_lib.activate
def test_posts_to_generic_webhook():
    responses_lib.add(
        responses_lib.POST,
        "https://example.com/webhook",
        json={"ok": True},
        status=200,
    )
    notifier = WebhookNotifier(url="https://example.com/webhook", format="generic", redact=True)
    notifier.report([_make_finding()])
    assert len(responses_lib.calls) == 1
    payload = responses_lib.calls[0].request.body
    import json
    data = json.loads(payload)
    assert "findings" in data
    assert data["findings"][0]["rule_id"] == "google-api-key"


@responses_lib.activate
def test_posts_slack_format():
    responses_lib.add(
        responses_lib.POST,
        "https://hooks.slack.com/services/abc",
        json={"ok": True},
        status=200,
    )
    notifier = WebhookNotifier(
        url="https://hooks.slack.com/services/abc", format="slack", redact=True
    )
    notifier.report([_make_finding()])
    assert len(responses_lib.calls) == 1
    import json
    data = json.loads(responses_lib.calls[0].request.body)
    assert "text" in data
    assert "google-api-key" in data["text"]


@responses_lib.activate
def test_no_post_when_no_findings():
    notifier = WebhookNotifier(url="https://example.com/webhook", format="generic", redact=True)
    notifier.report([])
    assert len(responses_lib.calls) == 0


@responses_lib.activate
def test_webhook_failure_does_not_raise(capsys):
    responses_lib.add(
        responses_lib.POST,
        "https://example.com/webhook",
        status=500,
    )
    notifier = WebhookNotifier(url="https://example.com/webhook", format="generic", redact=True)
    notifier.report([_make_finding()])  # must not raise
    captured = capsys.readouterr()
    assert "Warning" in captured.err
