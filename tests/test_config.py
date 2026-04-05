import tomllib
from pathlib import Path
import pytest
from keyguard.config import Config, load_config


def test_defaults_when_no_file(tmp_path):
    config = load_config(config_path=tmp_path / ".keyguard.toml")
    assert config.paths == ["."]
    assert config.exclude == []
    assert config.scan_git_history is True
    assert config.output_formats == ["terminal"]
    assert config.redact is True
    assert config.slack_webhook is None
    assert config.disabled_rules == []
    assert config.extra_rules == []


def test_loads_paths_and_exclude(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[scan]\npaths = ["src"]\nexclude = ["tests/", "*.example"]\n'
    )
    config = load_config(config_path=toml)
    assert config.paths == ["src"]
    assert config.exclude == ["tests/", "*.example"]


def test_loads_output_formats(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[output]\nformat = ["terminal", "json"]\n')
    config = load_config(config_path=toml)
    assert config.output_formats == ["terminal", "json"]


def test_loads_slack_webhook(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[notify]\nslack_webhook = "https://hooks.slack.com/abc"\n')
    config = load_config(config_path=toml)
    assert config.slack_webhook == "https://hooks.slack.com/abc"


def test_loads_disabled_rules(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[rules]\ndisabled = ["google-api-key"]\n')
    config = load_config(config_path=toml)
    assert "google-api-key" in config.disabled_rules


def test_invalid_toml_raises_value_error(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text("this is not valid toml ][[[")
    with pytest.raises(ValueError, match="Invalid"):
        load_config(config_path=toml)
