"""Unit tests for sourceosctl CLI commands."""

import json
import pathlib
import sys
import unittest
import tempfile
import os

# Ensure the repo root is on the path so tests work without installation.
_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.cli import build_parser, main
from sourceosctl.commands import doctor, profiles, nlboot, release, fingerprint, ai, agents, agent_machine


FIXTURES = _REPO_ROOT / "fixtures"


class _Args:
    """Minimal namespace helper for testing command functions directly."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestVersion(unittest.TestCase):
    def test_version_flag(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as cm:
            parser.parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)


class TestDoctor(unittest.TestCase):
    def test_doctor_returns_zero(self):
        args = _Args()
        result = doctor.run(args)
        self.assertIn(result, (0, None))

    def test_doctor_via_main(self):
        rc = main(["doctor"])
        self.assertEqual(rc, 0)


class TestProfiles(unittest.TestCase):
    def test_list_profiles_returns_zero(self):
        args = _Args()
        result = profiles.list_profiles(args)
        self.assertIn(result, (0, None))

    def test_profiles_list_via_main(self):
        rc = main(["profiles", "list"])
        self.assertEqual(rc, 0)


class TestNlboot(unittest.TestCase):
    def test_inspect_evidence_fixture(self):
        path = FIXTURES / "sample_nlboot_evidence.json"
        args = _Args(path=str(path), validate=False)
        result = nlboot.inspect_evidence(args)
        self.assertIn(result, (0, None))

    def test_inspect_evidence_missing_file(self):
        args = _Args(path="/nonexistent/path/evidence.json", validate=False)
        result = nlboot.inspect_evidence(args)
        self.assertEqual(result, 1)

    def test_inspect_evidence_bad_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not json {{{")
            tmp_path = f.name
        try:
            args = _Args(path=tmp_path, validate=False)
            result = nlboot.inspect_evidence(args)
            self.assertEqual(result, 1)
        finally:
            os.unlink(tmp_path)

    def test_nlboot_evidence_inspect_via_main(self):
        path = FIXTURES / "sample_nlboot_evidence.json"
        rc = main(["nlboot", "evidence", "inspect", str(path)])
        self.assertEqual(rc, 0)

    # --- schema validation ---

    def test_validate_evidence_valid_fixture(self):
        path = FIXTURES / "sample_nlboot_evidence.json"
        args = _Args(path=str(path))
        result = nlboot.validate_evidence(args)
        self.assertEqual(result, 0)

    def test_validate_evidence_invalid_fixture(self):
        path = FIXTURES / "invalid_nlboot_evidence.json"
        args = _Args(path=str(path))
        result = nlboot.validate_evidence(args)
        self.assertEqual(result, 1)

    def test_validate_evidence_missing_file(self):
        args = _Args(path="/nonexistent/evidence.json")
        result = nlboot.validate_evidence(args)
        self.assertEqual(result, 1)

    def test_validate_evidence_bad_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not json {{{")
            tmp_path = f.name
        try:
            args = _Args(path=tmp_path)
            result = nlboot.validate_evidence(args)
            self.assertEqual(result, 1)
        finally:
            os.unlink(tmp_path)

    def test_validate_evidence_unknown_schema(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"schemaVersion": "unknown-schema.v99", "kind": "Unknown"}, f)
            tmp_path = f.name
        try:
            args = _Args(path=tmp_path)
            result = nlboot.validate_evidence(args)
            self.assertEqual(result, 1)
        finally:
            os.unlink(tmp_path)

    def test_inspect_with_validate_flag_valid(self):
        path = FIXTURES / "sample_nlboot_evidence.json"
        rc = main(["nlboot", "evidence", "inspect", "--validate", str(path)])
        self.assertEqual(rc, 0)

    def test_inspect_with_validate_flag_invalid(self):
        path = FIXTURES / "invalid_nlboot_evidence.json"
        rc = main(["nlboot", "evidence", "inspect", "--validate", str(path)])
        self.assertEqual(rc, 1)

    def test_validate_subcommand_valid_via_main(self):
        path = FIXTURES / "sample_nlboot_evidence.json"
        rc = main(["nlboot", "evidence", "validate", str(path)])
        self.assertEqual(rc, 0)

    def test_validate_subcommand_invalid_via_main(self):
        path = FIXTURES / "invalid_nlboot_evidence.json"
        rc = main(["nlboot", "evidence", "validate", str(path)])
        self.assertEqual(rc, 1)


class TestRelease(unittest.TestCase):
    def test_inspect_fixture(self):
        path = FIXTURES / "sample_release.json"
        args = _Args(path=str(path))
        result = release.inspect(args)
        self.assertIn(result, (0, None))

    def test_inspect_missing_file(self):
        args = _Args(path="/nonexistent/release.json")
        result = release.inspect(args)
        self.assertEqual(result, 1)

    def test_inspect_bad_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("bad json")
            tmp_path = f.name
        try:
            args = _Args(path=tmp_path)
            result = release.inspect(args)
            self.assertEqual(result, 1)
        finally:
            os.unlink(tmp_path)

    def test_release_inspect_via_main(self):
        path = FIXTURES / "sample_release.json"
        rc = main(["release", "inspect", str(path)])
        self.assertEqual(rc, 0)


class TestReleaseArchive(unittest.TestCase):
    def test_inspect_archive_valid(self):
        path = FIXTURES / "nlboot_release_valid"
        args = _Args(path=str(path))
        result = release.inspect_archive(args)
        self.assertEqual(result, 0)

    def test_inspect_archive_invalid(self):
        path = FIXTURES / "nlboot_release_invalid"
        args = _Args(path=str(path))
        result = release.inspect_archive(args)
        self.assertEqual(result, 1)

    def test_inspect_archive_missing_dir(self):
        args = _Args(path="/nonexistent/nlboot_release")
        result = release.inspect_archive(args)
        self.assertEqual(result, 1)

    def test_inspect_archive_not_a_directory(self):
        path = FIXTURES / "sample_release.json"
        args = _Args(path=str(path))
        result = release.inspect_archive(args)
        self.assertEqual(result, 1)

    def test_inspect_archive_valid_via_main(self):
        path = FIXTURES / "nlboot_release_valid"
        rc = main(["release", "inspect-archive", str(path)])
        self.assertEqual(rc, 0)

    def test_inspect_archive_invalid_via_main(self):
        path = FIXTURES / "nlboot_release_invalid"
        rc = main(["release", "inspect-archive", str(path)])
        self.assertEqual(rc, 1)


class TestFingerprint(unittest.TestCase):
    def test_collect_dry_run(self):
        args = _Args(dry_run=True)
        result = fingerprint.collect(args)
        self.assertIn(result, (0, None))

    def test_collect_no_dry_run_rejected(self):
        args = _Args(dry_run=False)
        result = fingerprint.collect(args)
        self.assertEqual(result, 1)

    def test_fingerprint_collect_via_main(self):
        rc = main(["fingerprint", "collect", "--dry-run"])
        self.assertEqual(rc, 0)


class TestAi(unittest.TestCase):
    def test_list_labs_returns_zero(self):
        args = _Args()
        result = ai.list_labs(args)
        self.assertIn(result, (0, None))

    def test_ai_labs_list_via_main(self):
        rc = main(["ai", "labs", "list"])
        self.assertEqual(rc, 0)


class TestAgents(unittest.TestCase):
    def test_sandbox_plan_dry_run(self):
        args = _Args(dry_run=True)
        result = agents.sandbox_plan(args)
        self.assertIn(result, (0, None))

    def test_sandbox_plan_no_dry_run_rejected(self):
        args = _Args(dry_run=False)
        result = agents.sandbox_plan(args)
        self.assertEqual(result, 1)

    def test_agents_sandbox_plan_via_main(self):
        rc = main(["agents", "sandbox", "plan", "--dry-run"])
        self.assertEqual(rc, 0)


class TestAgentMachineMounts(unittest.TestCase):
    def test_mounts_plan_direct(self):
        args = _Args(
            profile="macos-podman",
            dev_root="~/dev",
            docs_root="~/Documents/SourceOS/agent-output",
            downloads_root="~/Downloads/SourceOS/agent-downloads",
        )
        result = agent_machine.mounts_plan(args)
        self.assertEqual(result, 0)

    def test_mounts_plan_via_main(self):
        rc = main([
            "agent-machine",
            "mounts",
            "plan",
            "--profile",
            "macos-podman",
            "--dev-root",
            "~/dev",
            "--docs-root",
            "~/Documents/SourceOS/agent-output",
            "--downloads-root",
            "~/Downloads/SourceOS/agent-downloads",
        ])
        self.assertEqual(rc, 0)

    def test_mounts_init_dry_run_via_main(self):
        rc = main([
            "agent-machine",
            "mounts",
            "init",
            "--dry-run",
        ])
        self.assertEqual(rc, 0)

    def test_mounts_init_no_dry_run_rejected(self):
        args = _Args(
            dry_run=False,
            profile="macos-podman",
            dev_root="~/dev",
            docs_root="~/Documents/SourceOS/agent-output",
            downloads_root="~/Downloads/SourceOS/agent-downloads",
        )
        result = agent_machine.mounts_init(args)
        self.assertEqual(result, 1)

    def test_mounts_inspect_omits_downloads_by_default(self):
        rc = main(["agent-machine", "mounts", "inspect"])
        self.assertEqual(rc, 0)

    def test_mounts_inspect_include_downloads(self):
        rc = main(["agent-machine", "mounts", "inspect", "--include-downloads"])
        self.assertEqual(rc, 0)

    def test_mounts_evidence_inspect_valid(self):
        payload = {
            "type": "AgentMachineMountEvidence",
            "workspaceId": "urn:srcos:agent-machine-workspace:test",
            "policyHash": "sha256:example",
            "mounts": [
                {"mountId": "dev-root", "pathClass": "code"},
                {"mountId": "browser-downloads", "pathClass": "downloads"},
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(payload, f)
            tmp_path = f.name
        try:
            rc = main(["agent-machine", "mounts", "evidence", "inspect", tmp_path])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(tmp_path)

    def test_mounts_evidence_inspect_missing(self):
        rc = main(["agent-machine", "mounts", "evidence", "inspect", "/nonexistent/mount-evidence.json"])
        self.assertEqual(rc, 1)

    def test_mounts_evidence_inspect_bad_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("bad json")
            tmp_path = f.name
        try:
            rc = main(["agent-machine", "mounts", "evidence", "inspect", tmp_path])
            self.assertEqual(rc, 1)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
