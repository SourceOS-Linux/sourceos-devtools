"""Unit tests for SourceOS Portable AI Kit commands."""

import hashlib
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

    def test_preflight_records_mount_and_host_facts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            captured = {}

            def capture(payload):
                captured.update(payload)
                return 0

            args = mock.Mock(target_root=tmpdir, benchmark=False)
            with mock.patch("sourceosctl.commands.portable_ai._print_json", side_effect=capture):
                self.assertEqual(portable_ai.preflight(args), 0)

            self.assertEqual(captured["type"], "PortablePreflightEvidence")
            self.assertIn("mount", captured)
            self.assertIn("host", captured)
            self.assertIn("disk", captured)
            self.assertIn("runtimePaths", captured)
            self.assertFalse(captured["benchmarkRequested"])
            self.assertFalse(captured["benchmarkPerformed"])
            self.assertFalse(captured["mutatesTarget"])

    def test_preflight_benchmark_removes_tempfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            before = set(os.listdir(tmpdir))
            result = portable_ai._benchmark(pathlib.Path(tmpdir), size_mb=1)
            after = set(os.listdir(tmpdir))
            self.assertTrue(result["requested"])
            self.assertTrue(result["performed"])
            self.assertTrue(result["tempFileRemoved"])
            self.assertEqual(before, after)
            self.assertGreater(result["writeMBps"], 0)
            self.assertGreater(result["readMBps"], 0)

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

    def test_byom_verify_dry_run_hashes_local_file_only(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            model = pathlib.Path(parent) / "demo.gguf"
            model.write_bytes(b"sourceos-test-model")
            expected_hash = hashlib.sha256(b"sourceos-test-model").hexdigest()
            captured = {}

            def capture(payload):
                captured.update(payload)
                return 0

            with mock.patch("sourceosctl.commands.portable_ai_byom._print_json", side_effect=capture):
                self.assertEqual(
                    portable_ai_main([
                        "byom",
                        "verify",
                        str(target),
                        str(model),
                        "--name",
                        "demo",
                    ]),
                    0,
                )

            self.assertEqual(captured["type"], "BYOMImportPlan")
            self.assertEqual(captured["sha256"], expected_hash)
            self.assertFalse(captured["downloadedModel"])
            self.assertTrue(captured["wouldWriteManifest"])
            self.assertFalse((target / "manifests").exists())

    def test_byom_execute_requires_policy_ok(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            model = pathlib.Path(parent) / "demo.gguf"
            model.write_bytes(b"sourceos-test-model")
            self.assertEqual(
                portable_ai_main([
                    "byom",
                    "verify",
                    str(target),
                    str(model),
                    "--execute",
                ]),
                0,
            )
            self.assertFalse((target / "manifests").exists())

    def test_byom_execute_writes_manifest_after_prepare(self):
        with tempfile.TemporaryDirectory() as parent:
            target = pathlib.Path(parent) / "SOURCEOS_AI"
            model = pathlib.Path(parent) / "demo.gguf"
            model.write_bytes(b"sourceos-test-model")
            evidence = pathlib.Path(parent) / "byom-evidence.json"

            self.assertEqual(
                portable_ai_main([
                    "prepare",
                    str(target),
                    "--profile",
                    "byom-gguf",
                    "--execute",
                    "--policy-ok",
                ]),
                0,
            )
            self.assertEqual(
                portable_ai_main([
                    "byom",
                    "verify",
                    str(target),
                    str(model),
                    "--name",
                    "demo",
                    "--execute",
                    "--policy-ok",
                    "--evidence-out",
                    str(evidence),
                ]),
                0,
            )
            manifest = target / "manifests" / "model-carry-pack.byom-gguf.demo.json"
            self.assertTrue(manifest.exists())
            self.assertTrue(evidence.exists())
            payload = json.loads(evidence.read_text())
            self.assertEqual(payload["type"], "BYOMImportEvidence")
            self.assertEqual(payload["decision"], "verified")
            self.assertTrue(payload["manifestWritten"])
            self.assertFalse(payload["downloadedModel"])

    def test_start_plan_emits_runtime_env_and_command_without_starting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            captured = {}

            def capture(payload):
                captured.update(payload)
                return 0

            with mock.patch("sourceosctl.commands.portable_ai_runtime._print_json", side_effect=capture):
                self.assertEqual(portable_ai_main(["start-plan", tmpdir, "--surface", "turtleterm"]), 0)

            self.assertEqual(captured["type"], "PortableAIStartPlan")
            self.assertEqual(captured["provider"], "ollama-compatible")
            self.assertEqual(captured["bindAddress"], "127.0.0.1")
            self.assertEqual(captured["port"], 11434)
            self.assertIn("OLLAMA_MODELS", captured["runtimeEnv"])
            self.assertEqual(captured["runtimeCommand"], ["ollama", "serve"])
            self.assertFalse(captured["wouldStartRuntime"])
            self.assertFalse(captured["wouldDownloadModel"])
            self.assertTrue(captured["requiresAgentMachineActivation"])

    def test_stop_plan_does_not_kill_processes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            captured = {}

            def capture(payload):
                captured.update(payload)
                return 0

            with mock.patch("sourceosctl.commands.portable_ai_runtime._print_json", side_effect=capture):
                self.assertEqual(portable_ai_main(["stop-plan", tmpdir]), 0)

            self.assertEqual(captured["type"], "PortableAIStopPlan")
            self.assertFalse(captured["wouldStopRuntime"])
            self.assertFalse(captured["wouldKillProcesses"])
            self.assertTrue(captured["requiresOperatorConfirmation"])
            self.assertTrue(captured["requiresAgentMachineTeardown"])

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
