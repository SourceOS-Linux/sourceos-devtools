"""Unit tests for SourceOS Portable AI Kit commands."""

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import portable_ai
from sourceosctl.commands.portable_ai_cli import main as portable_ai_main


class TestPortableAICommands(unittest.TestCase):
    def test_profiles_direct(self):
        self.assertEqual(portable_ai.profiles(mock.Mock()), 0)

    def test_profiles_cli(self):
        self.assertEqual(portable_ai_main(["profiles"]), 0)

    def test_preflight_existing_tempdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(portable_ai_main(["preflight", tmpdir]), 0)

    def test_prepare_dry_run_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            self.assertEqual(portable_ai_main(["prepare", str(target), "--profile", "tiny-router"]), 0)
            self.assertFalse(target.exists())

    def test_prepare_execute_requires_policy_ok(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            self.assertEqual(
                portable_ai_main(["prepare", str(target), "--execute", "--profile", "tiny-router"]),
                2,
            )
            self.assertFalse(target.exists())

    def test_prepare_execute_creates_manifest_and_evidence(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            evidence = pathlib.Path(parent) / "evidence.json"
            self.assertEqual(
                portable_ai_main([
                    "prepare",
                    str(target),
                    "--profile",
                    "laptop-safe",
                    "--execute",
                    "--policy-ok",
                    "--evidence-out",
                    str(evidence),
                ]),
                0,
            )
            self.assertTrue((target / "manifests" / "portable-ai-root.json").exists())
            self.assertTrue((target / "evidence" / "materialization").exists())
            self.assertTrue(evidence.exists())
            payload = json.loads(evidence.read_text())
            self.assertEqual(payload["type"], "PortableMaterializationEvidence")
            self.assertEqual(payload["profile"], "laptop-safe")
            self.assertFalse(payload["downloadedModels"])
            self.assertFalse(payload["startedRuntime"])

    def test_start_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(portable_ai_main(["start-plan", tmpdir, "--surface", "turtleterm"]), 0)

    def test_inspect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(portable_ai_main(["inspect", tmpdir]), 0)

    def test_evidence_inspect_valid(self):
        payload = {
            "type": "PortablePreflightEvidence",
            "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
            "targetRoot": "/tmp/SOURCEOS_AI",
            "decision": "pass",
            "promptEgressDefault": "deny",
            "hostWritesDefault": "deny",
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as handle:
            json.dump(payload, handle)
            tmp_path = handle.name
        try:
            self.assertEqual(portable_ai_main(["evidence", "inspect", tmp_path]), 0)
        finally:
            os.unlink(tmp_path)

    def test_evidence_inspect_missing(self):
        self.assertEqual(portable_ai_main(["evidence", "inspect", "/nonexistent/portable-ai.json"]), 1)


if __name__ == "__main__":
    unittest.main()
