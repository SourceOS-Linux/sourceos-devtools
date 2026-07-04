"""Unit tests for sourceosctl Network Door and Native Assistant Door commands."""

import json
import os
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import network


class TestNetworkDoorCommands(unittest.TestCase):
    def test_network_doctor(self):
        self.assertEqual(network.network_main(["doctor"]), 0)

    def test_network_plan_default_deny_hashes_destination(self):
        self.assertEqual(
            network.network_main([
                "plan",
                "--destination",
                "models.enterprise.example",
            ]),
            0,
        )

    def test_network_plan_enterprise_mesh_allow_listed(self):
        self.assertEqual(
            network.network_main([
                "plan",
                "--enterprise",
                "--mesh",
                "--allow-listed",
                "--destination",
                "models.enterprise.example",
            ]),
            0,
        )

    def test_network_provider_plan_byom(self):
        self.assertEqual(
            network.network_main([
                "provider",
                "--provider-class",
                "openai-compatible",
                "--owner",
                "user",
            ]),
            0,
        )

    def test_network_evidence_inspect_valid(self):
        payload = {
            "type": "NetworkDoorPlan",
            "decision": "deny",
            "destinationStored": False,
            "networkAccessProfileRef": "urn:srcos:network-access-profile:enterprise-and-user-default",
            "modelProviderRef": "urn:srcos:external-model-provider-profile:user-openai-compatible",
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as handle:
            json.dump(payload, handle)
            tmp_path = handle.name
        try:
            self.assertEqual(network.network_main(["evidence", "inspect", tmp_path]), 0)
        finally:
            os.unlink(tmp_path)

    def test_network_evidence_inspect_missing(self):
        self.assertEqual(network.network_main(["evidence", "inspect", "/nonexistent/network.json"]), 1)

    def test_native_assistant_plan_default(self):
        self.assertEqual(network.native_assistant_main(["plan"]), 0)

    def test_native_assistant_plan_hashes_prompt(self):
        self.assertEqual(
            network.native_assistant_main([
                "plan",
                "--operation",
                "create-office-artifact",
                "--prompt",
                "create a local report",
            ]),
            0,
        )

    def test_native_assistant_plan_cross_device_flag(self):
        self.assertEqual(
            network.native_assistant_main([
                "plan",
                "--platform",
                "cross-device",
                "--bridge-class",
                "mcp",
                "--operation",
                "handoff-to-agent-machine",
                "--allow-cross-device",
            ]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
