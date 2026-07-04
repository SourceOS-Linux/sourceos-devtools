"""Tests for local-agent registry drift checker."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts import check_local_agent_registry_drift


def write_minimal_repo(root: pathlib.Path) -> None:
    registry = root / "sourceosctl" / "local_agents"
    registry.mkdir(parents=True)
    (registry / "node-commander.json").write_text(json.dumps({
        "name": "node-commander",
        "label": "org.socioprophet.node-commander",
        "container": {
            "runtimeImage": "localhost/socioprophet/node-commander:dev-boot",
            "sourceImage": "us-central1-docker.pkg.dev/socioprophet-web/node-commander/node-commander:dev-boot",
        },
        "macos": {"launchd": {"plist": "~/Library/LaunchAgents/org.socioprophet.node-commander.plist"}},
    }))
    commands = root / "sourceosctl" / "commands"
    commands.mkdir(parents=True)
    (commands / "local_agent.py").write_text("localhost/socioprophet/node-commander:dev-boot us-central1-docker.pkg.dev/socioprophet-web/node-commander/node-commander:dev-boot org.socioprophet.node-commander")
    (commands / "local_agent_registry_cli.py").write_text("local_agent_registry_cli")
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "scan_local_persistence.py").write_text("RULES = []")
    bin_dir = root / "bin"
    bin_dir.mkdir()
    (bin_dir / "sourceos-agent").write_text("local_agent_registry_cli")
    (bin_dir / "sourceosctl").write_text("local_agent_registry_cli")


class TestLocalAgentRegistryDrift(unittest.TestCase):
    def test_repo_drift_check_passes(self):
        findings = check_local_agent_registry_drift.check_registry(_REPO_ROOT)
        highs = [f for f in findings if f.severity == "high"]
        self.assertEqual(highs, [])

    def test_minimal_repo_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_minimal_repo(root)
            findings = check_local_agent_registry_drift.check_registry(root)
        self.assertEqual(findings, [])

    def test_rejects_entrypoint_not_using_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_minimal_repo(root)
            (root / "bin" / "sourceos-agent").write_text("from sourceosctl.commands.local_agent import main")
            findings = check_local_agent_registry_drift.check_registry(root)
        self.assertTrue(any(f.severity == "high" and f.subject == "bin/sourceos-agent" for f in findings))

    def test_rejects_system_launchagent_registry_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_minimal_repo(root)
            reg = root / "sourceosctl" / "local_agents" / "node-commander.json"
            payload = json.loads(reg.read_text())
            payload["macos"]["launchd"]["plist"] = "/Library/LaunchAgents/org.socioprophet.node-commander.plist"
            reg.write_text(json.dumps(payload))
            findings = check_local_agent_registry_drift.check_registry(root)
        self.assertTrue(any(f.severity == "high" and "system-wide" in f.message for f in findings))

    def test_main_fail_on_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            write_minimal_repo(root)
            (root / "bin" / "sourceosctl").write_text("legacy route")
            rc = check_local_agent_registry_drift.main([str(root), "--fail-on", "high"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
