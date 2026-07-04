"""Tests for SourceOS contract validation and repo scanning commands."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import contracts


VALID_MANIFEST = {
    "repo": "SourceOS-Linux/sourceos-devtools",
    "domain": "tooling",
    "specVersion": "0.1.0",
    "ownedSchemas": [],
    "syncEngines": [],
    "sourceChannels": [],
    "policyClasses": ["high"],
    "auditEvents": ["devtools.contract.validated"],
    "dangerousSurfaces": ["devtools.schema.validation_bypass"],
}


class TestContractValidation(unittest.TestCase):
    def test_validate_repo_manifest_accepts_valid_manifest(self):
        errors = contracts.validate_repo_manifest(dict(VALID_MANIFEST))
        self.assertEqual(errors, [])

    def test_validate_repo_manifest_rejects_missing_required_field(self):
        payload = dict(VALID_MANIFEST)
        payload.pop("repo")
        errors = contracts.validate_repo_manifest(payload)
        self.assertIn("missing required field: repo", errors)

    def test_validate_repo_manifest_rejects_invalid_domain(self):
        payload = dict(VALID_MANIFEST)
        payload["domain"] = "unknown"
        errors = contracts.validate_repo_manifest(payload)
        self.assertTrue(any("domain must be one of" in error for error in errors))

    def test_validate_repo_manifest_rejects_invalid_policy_class(self):
        payload = dict(VALID_MANIFEST)
        payload["policyClasses"] = ["root"]
        errors = contracts.validate_repo_manifest(payload)
        self.assertIn("invalid policy class: root", errors)

    def test_contract_validate_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "manifest.json"
            path.write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            args = type("Args", (), {"path": str(path), "json": True})()
            self.assertEqual(contracts.contract_validate(args), 0)

    def test_contract_validate_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "manifest.json"
            path.write_text("not json", encoding="utf-8")
            args = type("Args", (), {"path": str(path), "json": True})()
            self.assertEqual(contracts.contract_validate(args), 1)


class TestRepoScan(unittest.TestCase):
    def test_repo_scan_valid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            manifest_dir = root / ".sourceos"
            manifest_dir.mkdir()
            (manifest_dir / "manifest.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            args = type("Args", (), {"path": str(root), "json": True})()
            self.assertEqual(contracts.repo_scan(args), 0)

    def test_repo_scan_missing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = type("Args", (), {"path": tmp, "json": True})()
            self.assertEqual(contracts.repo_scan(args), 1)

    def test_graph_and_sync_doctors_are_non_mutating(self):
        args = type("Args", (), {})()
        self.assertEqual(contracts.graph_doctor(args), 0)
        self.assertEqual(contracts.sync_doctor(args), 0)


if __name__ == "__main__":
    unittest.main()
