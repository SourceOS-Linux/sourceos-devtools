"""Unit tests for sourceosctl Office Plane commands."""

import json
import os
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.cli import main
from sourceosctl.commands import office


class _Args:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _office_args(**overrides):
    values = {
        "workroom_id": "workroom-test",
        "title": "Test Office Artifact",
        "artifact_type": "document",
        "format": "docx",
        "backend": "libreoffice",
        "mode": "local-headless",
        "output_root": "~/Documents/SourceOS/agent-output",
        "downloads_root": "~/Downloads/SourceOS/agent-downloads",
        "template_root": "~/dev",
        "execute": False,
        "policy_ok": False,
        "evidence_out": None,
    }
    values.update(overrides)
    return _Args(**values)


class TestOfficeCommands(unittest.TestCase):
    def test_office_doctor_direct(self):
        result = office.doctor(_Args())
        self.assertEqual(result, 0)

    def test_office_doctor_via_main(self):
        self.assertEqual(main(["office", "doctor"]), 0)

    def test_office_plan_via_main(self):
        rc = main([
            "office",
            "plan",
            "--workroom-id",
            "workroom-test",
            "--artifact-type",
            "slide-deck",
            "--format",
            "pptx",
            "--title",
            "Test Deck",
        ])
        self.assertEqual(rc, 0)

    def test_office_generate_dry_run_via_main(self):
        rc = main([
            "office",
            "generate",
            "--dry-run",
            "--artifact-type",
            "spreadsheet",
            "--format",
            "xlsx",
            "--title",
            "Test Sheet",
            "--template",
            "sourceos-office://templates/test-sheet",
            "--data-ref",
            "data://test",
        ])
        self.assertEqual(rc, 0)

    def test_office_generate_execute_requires_policy_ok(self):
        args = _office_args(
            execute=True,
            policy_ok=False,
            format="md",
            template=None,
            prompt_ref=None,
            data_ref=None,
        )
        self.assertEqual(office.generate(args), 1)

    def test_office_generate_execute_rejects_binary_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = _office_args(
                execute=True,
                policy_ok=True,
                format="docx",
                output_root=tmpdir,
                template=None,
                prompt_ref=None,
                data_ref=None,
            )
            self.assertEqual(office.generate(args), 1)

    def test_office_generate_execute_writes_markdown_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = os.path.join(tmpdir, "evidence", "office.json")
            rc = main([
                "office",
                "generate",
                "--execute",
                "--policy-ok",
                "--artifact-type",
                "document",
                "--format",
                "md",
                "--title",
                "Safe Report",
                "--output-root",
                tmpdir,
                "--evidence-out",
                evidence_path,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "safe-report.md")))
            with open(evidence_path, "r", encoding="utf-8") as handle:
                evidence = json.load(handle)
            self.assertEqual(evidence["kind"], "OfficeArtifactEvidence")
            self.assertEqual(evidence["operation"], "generate")
            self.assertEqual(evidence["status"], "requires-review")

    def test_office_generate_execute_rejects_whole_home_output_root(self):
        args = _office_args(
            execute=True,
            policy_ok=True,
            format="md",
            output_root="~",
            template=None,
            prompt_ref=None,
            data_ref=None,
        )
        self.assertEqual(office.generate(args), 1)

    def test_office_convert_dry_run_via_main(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", mode="w", delete=False) as handle:
            handle.write("placeholder")
            tmp_path = handle.name
        try:
            rc = main(["office", "convert", tmp_path, "--to", "pdf", "--dry-run"])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(tmp_path)

    def test_office_convert_execute_requires_policy_ok(self):
        args = _office_args(execute=True, policy_ok=False, input="/tmp/example.docx", to="pdf")
        self.assertEqual(office.convert(args), 1)

    def test_office_convert_execute_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = _office_args(
                execute=True,
                policy_ok=True,
                input="/nonexistent/example.docx",
                to="pdf",
                output_root=tmpdir,
            )
            self.assertEqual(office.convert(args), 1)

    def test_office_inspect_valid_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as handle:
            handle.write("hello")
            tmp_path = handle.name
        try:
            self.assertEqual(main(["office", "inspect", tmp_path]), 0)
        finally:
            os.unlink(tmp_path)

    def test_office_inspect_missing_file(self):
        self.assertEqual(main(["office", "inspect", "/nonexistent/office-artifact.docx"]), 1)

    def test_office_evidence_inspect_valid(self):
        payload = {
            "kind": "OfficeArtifactEvidence",
            "artifactId": "office-artifact-test",
            "workroomId": "workroom-test",
            "artifactType": "document",
            "format": "docx",
            "evidenceRefs": ["evidence://office/test"],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as handle:
            json.dump(payload, handle)
            tmp_path = handle.name
        try:
            self.assertEqual(main(["office", "evidence", "inspect", tmp_path]), 0)
        finally:
            os.unlink(tmp_path)

    def test_office_evidence_inspect_missing(self):
        self.assertEqual(main(["office", "evidence", "inspect", "/nonexistent/office-evidence.json"]), 1)

    def test_office_evidence_inspect_bad_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as handle:
            handle.write("bad json")
            tmp_path = handle.name
        try:
            self.assertEqual(main(["office", "evidence", "inspect", tmp_path]), 1)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
