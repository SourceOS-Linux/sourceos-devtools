"""Unit tests for SourceOS local-agent runtime CLI scaffold."""

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import local_agent


class TestLocalAgentParser(unittest.TestCase):
    def test_list_agents(self):
        rc = local_agent.main(["list"])
        self.assertEqual(rc, 0)

    def test_status_known_agent_with_mocked_checks(self):
        with mock.patch.object(local_agent, "collect_checks", return_value=[]):
            rc = local_agent.main(["status", "node-commander"])
        self.assertEqual(rc, 0)

    def test_preflight_fails_for_unknown_agent(self):
        with self.assertRaises(SystemExit):
            local_agent.main(["preflight", "missing-agent"])

    def test_mutating_command_is_plan_only_without_execute_policy_ok(self):
        rc = local_agent.main(["quarantine", "node-commander"])
        self.assertEqual(rc, 0)

    def test_mutating_command_refuses_partial_scaffold_with_execute_policy_ok(self):
        rc = local_agent.main(["quarantine", "node-commander", "--execute", "--policy-ok"])
        self.assertEqual(rc, 1)


class TestLocalAgentChecks(unittest.TestCase):
    def test_empty_authfile_detection(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            f.write('{"auths":{}}')
            f.flush()
            ok, detail = local_agent._authfile_is_empty_auth(pathlib.Path(f.name))
        self.assertTrue(ok)
        self.assertIn("empty authfile", detail)

    def test_non_empty_authfile_detection(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            f.write('{"auths":{"example.com":{"auth":"secret"}}}')
            f.flush()
            ok, detail = local_agent._authfile_is_empty_auth(pathlib.Path(f.name))
        self.assertFalse(ok)
        self.assertIn("not empty-authfile", detail)

    def test_runtime_image_policy_is_localhost(self):
        agent = local_agent.DEFAULT_AGENTS["node-commander"]
        self.assertTrue(agent.runtime_image.startswith("localhost/"))
        self.assertIn("us-central1-docker.pkg.dev", agent.source_image)

    def test_guarded_mutation_requires_both_execute_and_policy_ok(self):
        parser = local_agent.build_parser()
        args = parser.parse_args(["install", "node-commander", "--execute"])
        self.assertTrue(args.execute)
        self.assertFalse(args.policy_ok)


if __name__ == "__main__":
    unittest.main()
