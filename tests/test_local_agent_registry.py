"""Tests for local-agent registry validation."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts import validate_local_agents


def valid_payload():
    return {
        "schemaVersion": "sourceos.local-agent.v1",
        "name": "node-commander",
        "label": "org.socioprophet.node-commander",
        "scope": "user",
        "runtime": "podman",
        "owner": {"project": "SocioProphet", "component": "node-commander", "contact": "platform"},
        "container": {
            "name": "node-commander",
            "runtimeImage": "localhost/socioprophet/node-commander:dev-boot",
            "sourceImage": "us-central1-docker.pkg.dev/socioprophet-web/node-commander/node-commander:dev-boot",
            "pullPolicy": "never",
        },
        "podman": {"connection": "podman-machine-default", "requireMachine": True, "requireLocalImage": True, "rootless": True},
        "auth": {
            "mode": "empty-authfile",
            "authfile": "~/.config/containers/empty-auth.json",
            "allowAmbientDockerConfig": False,
            "allowInteractiveCredentialHelper": False,
        },
        "macos": {
            "launchd": {
                "plist": "~/Library/LaunchAgents/org.socioprophet.node-commander.plist",
                "legacySystemPlist": "/Library/LaunchAgents/org.socioprophet.node-commander.plist",
                "runAtLoad": True,
                "keepAlive": False,
            }
        },
        "linux": {
            "systemdUserUnit": "~/.config/systemd/user/org.socioprophet.node-commander.service",
            "restart": "on-failure",
            "restartSec": 10,
            "startLimitIntervalSec": 3600,
            "startLimitBurst": 3,
        },
        "logs": {"directory": "~/Library/Logs/SocioProphet", "app": "~/Library/Logs/SocioProphet/node-commander.log"},
        "health": {"type": "podman-container", "expected": "running"},
        "quarantine": {
            "captureServiceDefinition": True,
            "captureLogs": True,
            "captureRuntimeState": True,
            "captureImageMetadata": True,
            "captureRedactedAuthConfig": True,
        },
    }


class TestLocalAgentRegistryValidator(unittest.TestCase):
    def test_valid_payload_has_no_findings(self):
        findings = validate_local_agents.validate_payload(pathlib.Path("agent.json"), valid_payload())
        self.assertEqual(findings, [])

    def test_rejects_non_localhost_runtime_image(self):
        payload = valid_payload()
        payload["container"]["runtimeImage"] = payload["container"]["sourceImage"]
        findings = validate_local_agents.validate_payload(pathlib.Path("agent.json"), payload)
        self.assertIn("container.runtimeImage", {f.field for f in findings})

    def test_rejects_keepalive_true(self):
        payload = valid_payload()
        payload["macos"]["launchd"]["keepAlive"] = True
        findings = validate_local_agents.validate_payload(pathlib.Path("agent.json"), payload)
        self.assertIn("macos.launchd.keepAlive", {f.field for f in findings})

    def test_validate_registry_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            reg = root / "sourceosctl" / "local_agents"
            reg.mkdir(parents=True)
            (reg / "node-commander.json").write_text(json.dumps(valid_payload()))
            findings = validate_local_agents.validate(root)
        self.assertEqual(findings, [])

    def test_main_returns_one_for_bad_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            reg = root / "sourceosctl" / "local_agents"
            reg.mkdir(parents=True)
            bad = valid_payload()
            bad["auth"]["allowInteractiveCredentialHelper"] = True
            (reg / "bad.json").write_text(json.dumps(bad))
            rc = validate_local_agents.main([str(root)])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
