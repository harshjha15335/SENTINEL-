"""Offline proposal regression checks; requires pytest and PyYAML in the review environment."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def proposal():
    return yaml.safe_load((ROOT / "deploy/render-continuous.yaml").read_text())


def test_restarts_do_not_reset_seed_account_passwords():
    # Bootstrap secrets belong to the one-off command, not every service process/restart.
    env = proposal()["services"][0]["envVars"]
    assert not any(item["key"].startswith("SENTINEL_SEED_") for item in env)


def test_hosted_proposal_requires_explicit_proxy_trust_and_single_instance():
    service = proposal()["services"][0]
    env = {item["key"]: item for item in service["envVars"]}
    assert service["numInstances"] == 1
    assert service["autoDeploy"] is False
    assert env["SENTINEL_FORWARDED_ALLOW_IPS"] == {
        "key": "SENTINEL_FORWARDED_ALLOW_IPS",
        "sync": False,
    }
    assert service["healthCheckPath"] == "/api/v1/ready"
