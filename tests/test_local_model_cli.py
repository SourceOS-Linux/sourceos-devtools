"""Unit tests for sourceosctl Local Model Door commands."""

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.cli import main
from sourceosctl.commands import local_model


class TestLocalModelCommands(unittest.TestCase):
    def test_profiles_direct(self):
        self.assertEqual(local_model.profiles(mock.Mock()), 0)

    @mock.patch("sourceosctl.commands.local_model.shutil.which", return_value=None)
    def test_doctor_without_ollama(self, _which):
        self.assertEqual(main(["local-model", "doctor"]), 0)

    @mock.patch("sourceosctl.commands.local_model.shutil.which", return_value="/usr/bin/ollama")
    @mock.patch("sourceosctl.commands.local_model.subprocess.run")
    def test_doctor_with_ollama_models(self, run, _which):
        run.return_value = mock.Mock(
            returncode=0,
            stdout="NAME ID SIZE MODIFIED\nllama3.2:1b abc 1.3 GB now\n",
            stderr="",
        )
        self.assertEqual(main(["local-model", "doctor"]), 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["/usr/bin/ollama", "list"])

    @mock.patch("sourceosctl.commands.local_model.shutil.which", return_value=None)
    def test_plan_does_not_pull_model(self, _which):
        self.assertEqual(main(["local-model", "plan", "--profile", "local-llama32-1b"]), 0)

    @mock.patch("sourceosctl.commands.local_model.shutil.which", return_value=None)
    def test_route_hash_only_with_prompt(self, _which):
        self.assertEqual(
            main([
                "local-model",
                "route",
                "--task-class",
                "office-assist",
                "--prompt",
                "sensitive prompt body should not be emitted",
                "--personalization-ref",
                "urn:socioprophet:personal-tuning-contract:demo-user-local-llama32",
            ]),
            0,
        )

    def test_evidence_inspect_valid(self):
        payload = {
            "type": "LocalModelRouteDecision",
            "taskClass": "office-assist",
            "target": "personal-local-policy-checked",
            "promptStored": False,
            "promptHash": "sha256:example",
            "routerBindingRef": "urn:socioprophet:model-router-binding:demo-user-local-llama32",
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as handle:
            json.dump(payload, handle)
            tmp_path = handle.name
        try:
            self.assertEqual(main(["local-model", "evidence", "inspect", tmp_path]), 0)
        finally:
            os.unlink(tmp_path)

    def test_evidence_inspect_missing(self):
        self.assertEqual(main(["local-model", "evidence", "inspect", "/nonexistent/local-model.json"]), 1)


if __name__ == "__main__":
    unittest.main()
