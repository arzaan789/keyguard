from pathlib import Path
from keyguard.config import load_config, CiConfig


def test_ci_section_absent_returns_none(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text('[scan]\npaths = ["."]\n')
    config = load_config(config_path=toml)
    assert config.ci is None


def test_ci_tokens_loaded(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\n'
        'github_token = "ghp_abc"\n'
        'circleci_token = "CCIPAT_xyz"\n'
        'gitlab_token = "glpat-123"\n'
        'max_runs = 5\n'
    )
    config = load_config(config_path=toml)
    assert config.ci is not None
    assert config.ci.github_token == "ghp_abc"
    assert config.ci.circleci_token == "CCIPAT_xyz"
    assert config.ci.gitlab_token == "glpat-123"
    assert config.ci.max_runs == 5


def test_ci_github_orgs_loaded(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\ngithub_token = "ghp_abc"\n'
        '[ci.github]\norgs = ["my-org"]\nrepos = ["my-org/specific"]\n'
    )
    config = load_config(config_path=toml)
    assert config.ci.github_orgs == ["my-org"]
    assert config.ci.github_repos == ["my-org/specific"]


def test_ci_gitlab_custom_url(tmp_path):
    toml = tmp_path / ".keyguard.toml"
    toml.write_text(
        '[ci]\ngitlab_token = "glpat-123"\ngitlab_url = "https://gitlab.mycompany.com"\n'
        '[ci.gitlab]\ngroups = ["my-group"]\n'
    )
    config = load_config(config_path=toml)
    assert config.ci.gitlab_url == "https://gitlab.mycompany.com"
    assert config.ci.gitlab_groups == ["my-group"]


def test_ciconfig_defaults():
    ci = CiConfig()
    assert ci.github_token is None
    assert ci.gitlab_url == "https://gitlab.com"
    assert ci.max_runs == 10
    assert ci.github_orgs == []
