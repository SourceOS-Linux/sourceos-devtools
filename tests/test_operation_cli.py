"""Unit tests for sourceosctl operation commands."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import operation


FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "workspace-operation" / "minimal-operation.json"


class TestOperationCommands(unittest.TestCase):
    def test_validate_fixture_passes_for_minimal_operation(self):
        self.assertEqual(operation.operation_main(["validate-fixture", str(FIXTURE), "--structural-only"]), 0)

    def test_conformance_passes_for_local_fixture_dir(self):
        fixture_dir = FIXTURE.parent
        self.assertEqual(
            operation.operation_main(
                [
                    "conformance",
                    "--examples-dir",
                    str(fixture_dir),
                    "--schemas-dir",
                    str(_REPO_ROOT / "fixtures" / "schemas"),
                    "--structural-only",
                ]
            ),
            0,
        )

    def test_replay_fixture_generates_browser_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "browser-replay.json"
            rc = operation.operation_main(["replay-fixture", str(out), "--surface", "browser-capture"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["operation"]["operation_type"], "sourceos.browser-capture.replay")
            self.assertEqual(payload["event"]["event_type"], "browser-capture.completed")

    def test_scaffold_adapter_writes_three_skeletons(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp) / "adapter"
            rc = operation.operation_main(["scaffold-adapter", str(out_dir)])
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "terminal-command.adapter.json").exists())
            self.assertTrue((out_dir / "browser-capture.adapter.json").exists())
            self.assertTrue((out_dir / "local-agent-execution.adapter.json").exists())


if __name__ == "__main__":
    unittest.main()
