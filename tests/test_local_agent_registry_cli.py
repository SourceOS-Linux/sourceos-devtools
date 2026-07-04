"""Tests for registry-backed local-agent CLI adapter."""

import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import local_agent
from sourceosctl.commands import local_agent_registry_cli


class TestLocalAgentRegistryCli(unittest.TestCase):
    def test_load_registry_into_cli_populates_default_agents(self):
        agents = local_agent_registry_cli.load_registry_into_cli()
        self.assertIn("node-commander", agents)
        self.assertIn("node-commander", local_agent.DEFAULT_AGENTS)
        self.assertEqual(
            local_agent.DEFAULT_AGENTS["node-commander"].runtime_image,
            "localhost/socioprophet/node-commander:dev-boot",
        )

    def test_json_list(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = local_agent_registry_cli.main(["list", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertIn("agents", payload)
        self.assertEqual(payload["agents"][0]["name"], "node-commander")

    def test_json_status_with_mocked_checks(self):
        out = io.StringIO()
        check = local_agent.Check("agent", "pass", "ok")
        with mock.patch.object(local_agent, "collect_checks", return_value=[check]):
            with redirect_stdout(out):
                rc = local_agent_registry_cli.main(["status", "node-commander", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["agent"]["name"], "node-commander")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checks"][0]["name"], "agent")

    def test_json_status_unknown_agent(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = local_agent_registry_cli.main(["status", "missing", "--json"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown local agent", err.getvalue())

    def test_non_json_delegates_to_existing_cli(self):
        with mock.patch.object(local_agent, "main", return_value=0) as mocked:
            rc = local_agent_registry_cli.main(["list"])
        self.assertEqual(rc, 0)
        mocked.assert_called_once_with(["list"])


if __name__ == "__main__":
    unittest.main()
