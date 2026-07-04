"""Tests for SourceOS Mutation and Evidence Accountability devtools CLI."""

from __future__ import annotations

import pathlib
import stat
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.cli import main
from sourceosctl.commands import mutation_evidence


REQUIRED_SPEC_PATHS = mutation_evidence.REQUIRED_SPEC_PATHS


def _make_spec_root(tmpdir: pathlib.Path, validator_exit: int = 0) -> pathlib.Path:
    """Create a minimal sourceos-spec-like tree for CLI tests."""
    spec_root = tmpdir / "sourceos-spec"
    spec_root.mkdir()
    for rel in REQUIRED_SPEC_PATHS:
        path = spec_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("validate_mutation_evidence_accountability.py"):
            path.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                f"print('validator fixture exit={validator_exit}')\n"
                f"raise SystemExit({validator_exit})\n"
            )
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        else:
            path.write_text("{}\n")
    return spec_root


class TestMutationEvidenceCli(unittest.TestCase):
    def test_plan_returns_zero_for_default_spec_root(self):
        rc = main(["mutation-evidence", "plan"])
        self.assertEqual(rc, 0)

    def test_fixture_plan_returns_zero(self):
        rc = main(["mutation-evidence", "fixture-plan"])
        self.assertEqual(rc, 0)

    def test_inspect_missing_spec_root_fails(self):
        rc = main(["mutation-evidence", "inspect", "--spec-root", "/nonexistent/sourceos-spec"])
        self.assertEqual(rc, 1)

    def test_inspect_complete_spec_root_passes(self):
        with tempfile.TemporaryDirectory() as td:
            spec_root = _make_spec_root(pathlib.Path(td))
            rc = main(["mutation-evidence", "inspect", "--spec-root", str(spec_root)])
            self.assertEqual(rc, 0)

    def test_validate_complete_spec_root_passes_when_validator_passes(self):
        with tempfile.TemporaryDirectory() as td:
            spec_root = _make_spec_root(pathlib.Path(td), validator_exit=0)
            rc = main(["mutation-evidence", "validate", "--spec-root", str(spec_root)])
            self.assertEqual(rc, 0)

    def test_validate_complete_spec_root_fails_when_validator_fails(self):
        with tempfile.TemporaryDirectory() as td:
            spec_root = _make_spec_root(pathlib.Path(td), validator_exit=7)
            rc = main(["mutation-evidence", "validate", "--spec-root", str(spec_root)])
            self.assertEqual(rc, 7)


if __name__ == "__main__":
    unittest.main()
