"""Tests for local-agent registry loader."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.local_agents import registry


def payload():
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


class TestLocalAgentRegistryLoader(unittest.TestCase):
    def test_load_repo_registry(self):
        records = registry.load_records()
        self.assertIn("node-commander", records)
        record = records["node-commander"]
        self.assertEqual(record.runtime_image, "localhost/socioprophet/node-commander:dev-boot")
        self.assertIn("us-central1-docker.pkg.dev", record.source_image)
        self.assertEqual(record.user_plist, "~/Library/LaunchAgents/org.socioprophet.node-commander.plist")

    def test_load_record_from_temp_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "node-commander.json").write_text(json.dumps(payload()))
            records = registry.load_records(root)
        self.assertEqual(set(records), {"node-commander"})
        self.assertEqual(records["node-commander"].podman_connection, "podman-machine-default")

    def test_duplicate_names_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "a.json").write_text(json.dumps(payload()))
            (root / "b.json").write_text(json.dumps(payload()))
            with self.assertRaises(ValueError):
                registry.load_records(root)

    def test_missing_required_field_raises(self):
        bad = payload()
        del bad["container"]["runtimeImage"]
        with self.assertRaises(ValueError):
            registry.normalize(bad)

    def test_load_record_or_error_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                registry.load_record_or_error("missing", pathlib.Path(tmp))


if __name__ == "__main__":
    unittest.main()
