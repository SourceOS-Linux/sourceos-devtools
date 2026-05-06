"""Unit tests for sourceosctl reasoning commands."""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import reasoning


FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "reasoning" / "deterministic"


class TestReasoningCommands(unittest.TestCase):
    def test_reasoning_validate_passes_for_fixture(self):
        self.assertEqual(reasoning.reasoning_main(["validate", str(FIXTURE)]), 0)

    def test_reasoning_inspect_passes_for_fixture(self):
        self.assertEqual(reasoning.reasoning_main(["inspect", str(FIXTURE)]), 0)

    def test_reasoning_replay_plan_passes_for_fixture(self):
        self.assertEqual(reasoning.reasoning_main(["replay-plan", str(FIXTURE)]), 0)

    def test_reasoning_events_passes_for_fixture(self):
        self.assertEqual(reasoning.reasoning_main(["events", str(FIXTURE)]), 0)

    def test_validate_run_dir_returns_structured_pass(self):
        report = reasoning.validate_run_dir(FIXTURE)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["runId"], "urn:srcos:reasoning-run:sourceosctl-fixture")
        self.assertEqual(report["replayClass"], "exact")
        self.assertTrue(report["benchmarkPassed"])
        self.assertEqual(report["rawPrivateReasoning"], "not-collected")

    def test_reasoning_validate_fails_closed_when_benchmark_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            for source in FIXTURE.iterdir():
                shutil.copy(source, tmp_path / source.name)
            os.unlink(tmp_path / "reasoning-benchmark.json")

            report = reasoning.validate_run_dir(tmp_path)

        self.assertEqual(report["result"], "fail")
        self.assertIn("missing canonical artifact: reasoning-benchmark.json", report["errors"])

    def test_reasoning_validate_fails_on_raw_private_reasoning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            for source in FIXTURE.iterdir():
                shutil.copy(source, tmp_path / source.name)
            run_path = tmp_path / "reasoning-run.sourceos.json"
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            payload["safeTrace"]["rawPrivateReasoning"] = "present"
            run_path.write_text(json.dumps(payload), encoding="utf-8")

            report = reasoning.validate_run_dir(tmp_path)

        self.assertEqual(report["result"], "fail")
        self.assertIn("raw private reasoning must be not-collected", report["errors"])


if __name__ == "__main__":
    unittest.main()
