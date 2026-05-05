"""Tests for SourceOS Office runtime contract evidence projection."""

import json
import os
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import office
from sourceosctl.commands.office_runtime_contracts import (
    build_office_runtime_contracts,
    execution_backend,
)


class _Args:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _office_args(**overrides):
    values = {
        "workroom_id": "workroom-test",
        "title": "Runtime Contract Report",
        "artifact_type": "document",
        "format": "md",
        "backend": "libreoffice",
        "mode": "local-headless",
        "output_root": "~/Documents/SourceOS/agent-output",
        "downloads_root": "~/Downloads/SourceOS/agent-downloads",
        "template_root": "~/dev",
        "execute": False,
        "policy_ok": False,
        "evidence_out": None,
        "template": None,
        "prompt_ref": None,
        "data_ref": None,
    }
    values.update(overrides)
    return _Args(**values)


class TestOfficeRuntimeContracts(unittest.TestCase):
    def test_execution_backend_never_maps_remote_api_to_microsoft_graph(self):
        self.assertEqual(execution_backend("sourceos-remote", "remote-api"), "SOURCEOS_NATIVE")
        self.assertEqual(execution_backend("microsoft-graph", "remote-api"), "OTHER_OPEN")

    def test_guarded_generate_evidence_contains_runtime_contract_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "evidence", "office.json")
            args = _office_args(
                execute=True,
                policy_ok=True,
                output_root=tmpdir,
                evidence_out=evidence_path,
            )

            self.assertEqual(office.generate(args), 0)

            with open(evidence_path, "r", encoding="utf-8") as handle:
                evidence = json.load(handle)

            contracts = evidence["officeRuntimeContracts"]
            self.assertIn("officeDocumentRecord", contracts)
            self.assertIn("officeSessionRecord", contracts)
            self.assertIn("officeVersionRecord", contracts)
            self.assertIn("officeWritebackRecord", contracts)

            document = contracts["officeDocumentRecord"]
            session = contracts["officeSessionRecord"]
            version = contracts["officeVersionRecord"]
            writeback = contracts["officeWritebackRecord"]

            self.assertEqual(document["source_provider"], "SOURCEOS")
            self.assertEqual(document["editor_binding"], "LOCAL_LIBREOFFICE")
            self.assertEqual(session["status"], "CLOSED")
            self.assertEqual(version["source_provider"], "SOURCEOS")
            self.assertEqual(version["execution_backend"], "LIBREOFFICE")
            self.assertEqual(version["capture_source"], "SYSTEM_WORKFLOW")
            self.assertTrue(version["content_hash"].startswith("sha256:"))
            self.assertEqual(writeback["operation"], "LOCAL_SAVE")
            self.assertEqual(writeback["source"], "LOCAL_CLI")
            self.assertEqual(writeback["result_version_id"], version["version_id"])

    def test_runtime_contracts_not_built_without_materialized_hashes(self):
        plan = {
            "officeArtifact": {
                "artifactId": "office-artifact-nohash",
                "workroomId": "workroom-test",
                "format": "md",
                "storageRef": "sourceos-office://workroom-test/output/nohash.md",
                "backend": {"engine": "libreoffice", "mode": "local-headless"},
            }
        }
        evidence = {
            "operation": "generate",
            "capturedAt": "2026-05-05T00:00:00+00:00",
            "artifactHashes": [],
        }

        self.assertIsNone(build_office_runtime_contracts(plan=plan, evidence=evidence))

    def test_evidence_inspect_accepts_runtime_contract_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "evidence", "office.json")
            args = _office_args(
                execute=True,
                policy_ok=True,
                output_root=tmpdir,
                evidence_out=evidence_path,
            )
            self.assertEqual(office.generate(args), 0)
            self.assertEqual(office.evidence_inspect(_Args(path=evidence_path)), 0)


if __name__ == "__main__":
    unittest.main()
