"""Guarded execution tests for Agent Machine mount materialization."""

import json
import os
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.cli import main


class TestAgentMachineGuardedExecution(unittest.TestCase):
    def test_mounts_init_execute_requires_policy_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main([
                "agent-machine",
                "mounts",
                "init",
                "--execute",
                "--dev-root",
                os.path.join(tmpdir, "dev"),
                "--docs-root",
                os.path.join(tmpdir, "office-output"),
                "--downloads-root",
                os.path.join(tmpdir, "agent-downloads"),
            ])
            self.assertEqual(rc, 1)

    def test_mounts_init_execute_creates_only_scoped_dirs_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_root = os.path.join(tmpdir, "dev")
            docs_root = os.path.join(tmpdir, "office-output")
            downloads_root = os.path.join(tmpdir, "agent-downloads")
            evidence_path = os.path.join(tmpdir, "evidence", "mounts.json")

            os.makedirs(dev_root)

            rc = main([
                "agent-machine",
                "mounts",
                "init",
                "--execute",
                "--policy-ok",
                "--dev-root",
                dev_root,
                "--docs-root",
                docs_root,
                "--downloads-root",
                downloads_root,
                "--evidence-out",
                evidence_path,
            ])

            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isdir(dev_root))
            self.assertTrue(os.path.isdir(docs_root))
            self.assertTrue(os.path.isdir(downloads_root))
            self.assertTrue(os.path.exists(evidence_path))

            with open(evidence_path, "r", encoding="utf-8") as handle:
                evidence = json.load(handle)

            self.assertEqual(evidence["kind"], "AgentMachineMountEvidence")
            self.assertEqual(evidence["backendIntent"], "agent-machine")
            self.assertEqual(evidence["mountPolicyRef"], "urn:srcos:agent-machine-mount-policy:default-deny-scoped-roots")
            self.assertEqual(len(evidence["mounts"]), 3)
            self.assertTrue(any(m["pathClass"] == "downloads" for m in evidence["mounts"]))

    def test_mounts_init_rejects_unscoped_downloads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main([
                "agent-machine",
                "mounts",
                "init",
                "--execute",
                "--policy-ok",
                "--dev-root",
                os.path.join(tmpdir, "dev"),
                "--docs-root",
                os.path.join(tmpdir, "office-output"),
                "--downloads-root",
                "~/Downloads",
            ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
