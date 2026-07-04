"""Unit tests for SourceOS local-agent runtime CLI scaffold."""

import json
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

    def test_stage_executes_with_execute_and_policy_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = local_agent.main(["stage", "node-commander", "--execute", "--policy-ok", "--output-dir", tmp])
            self.assertEqual(rc, 0)
            dirs = list(pathlib.Path(tmp).glob("node-commander-*"))
            self.assertEqual(len(dirs), 1)
            self.assertTrue((dirs[0] / "bin" / "node-commander-launch").exists())
            self.assertTrue((dirs[0] / "launchd" / "org.socioprophet.node-commander.plist").exists())
            self.assertTrue((dirs[0] / "systemd-user" / "org.socioprophet.node-commander.service").exists())
            self.assertTrue((dirs[0] / "agent.json").exists())

    def test_install_plan_only(self):
        rc = local_agent.main(["install", "node-commander"])
        self.assertEqual(rc, 0)

    def test_install_force_executes_with_mocked_runtime_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = local_agent.DEFAULT_AGENTS["node-commander"]
            patched = local_agent.LocalAgent(
                **{**agent.__dict__,
                   "authfile": str(pathlib.Path(tmp) / "empty-auth.json"),
                   "user_plist": str(pathlib.Path(tmp) / "LaunchAgents" / "org.socioprophet.node-commander.plist"),
                   "log_dir": str(pathlib.Path(tmp) / "Logs"),
                   "app_log": str(pathlib.Path(tmp) / "Logs" / "node-commander.log")}
            )
            with mock.patch.dict(local_agent.DEFAULT_AGENTS, {"node-commander": patched}), \
                mock.patch.object(local_agent, "_runtime_blocking_failures", return_value=[]), \
                mock.patch.object(local_agent, "platform") as platform_mod:
                platform_mod.system.return_value = "Darwin"
                platform_mod.platform.return_value = "test-platform"
                rc = local_agent.main(["install", "node-commander", "--execute", "--policy-ok", "--force"])
            self.assertEqual(rc, 0)
            self.assertTrue(pathlib.Path(patched.user_plist).exists())
            self.assertTrue(pathlib.Path(patched.authfile).exists())

    def test_quarantine_executes_with_execute_and_policy_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(local_agent, "collect_checks", return_value=[]), \
                mock.patch.object(local_agent, "_capture_launchd", return_value=[]), \
                mock.patch.object(local_agent, "_capture_podman", return_value=[]), \
                mock.patch.object(local_agent, "_capture_redacted_auth", return_value=[]):
                rc = local_agent.main([
                    "quarantine",
                    "node-commander",
                    "--execute",
                    "--policy-ok",
                    "--output-dir",
                    tmp,
                ])
            self.assertEqual(rc, 0)
            dirs = list(pathlib.Path(tmp).glob("node-commander-*"))
            self.assertEqual(len(dirs), 1)
            self.assertTrue((dirs[0] / "manifest.json").exists())
            self.assertTrue((dirs[0] / "remediation.md").exists())

    def test_start_refuses_blocking_preflight_failure(self):
        failure = local_agent.Check("podman-socket", "fail", "socket refused")
        with mock.patch.object(local_agent, "_runtime_blocking_failures", return_value=[failure]):
            rc = local_agent.main(["start", "node-commander", "--execute", "--policy-ok"])
        self.assertEqual(rc, 1)

    def test_stop_executes_with_mocked_backends(self):
        with mock.patch.object(local_agent, "_launchctl_binary", return_value=None), \
            mock.patch.object(local_agent, "_podman_binary", return_value=None):
            rc = local_agent.main(["stop", "node-commander", "--execute", "--policy-ok"])
        self.assertEqual(rc, 0)

    def test_uninstall_plan_only(self):
        rc = local_agent.main(["uninstall", "node-commander"])
        self.assertEqual(rc, 0)


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

    def test_redacted_json_masks_auth(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump({"auths": {"example.com": {"auth": "secret"}}}, f)
            f.flush()
            redacted = local_agent._redacted_json(pathlib.Path(f.name))
        self.assertIn("<redacted>", redacted)
        self.assertNotIn("secret", redacted)

    def test_rendered_launcher_uses_empty_authfile_and_local_image(self):
        agent = local_agent.DEFAULT_AGENTS["node-commander"]
        launcher = local_agent._render_launcher(agent)
        self.assertIn("--authfile", launcher)
        self.assertIn(agent.runtime_image, launcher)
        self.assertNotIn(agent.source_image, launcher)


if __name__ == "__main__":
    unittest.main()
