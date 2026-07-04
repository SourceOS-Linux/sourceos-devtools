"""Mutation and Evidence Accountability developer helpers.

This module intentionally treats sourceos-spec as the canonical schema home.
Devtools provides the operator/developer CLI wrapper and posture checks so every
implementation repo can validate against the same contract instead of copying
schema logic.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass


REQUIRED_SPEC_PATHS = [
    "schemas/MutationEvidenceAccountability.schema.json",
    "schemas/MutationEvidenceUmbrellaPrimitives.schema.json",
    "examples/mutation-evidence-accountability.examples.json",
    "examples/mutation-evidence-umbrella.examples.json",
    "fixtures/anti-patterns/mutation-evidence-accountability.invalid.json",
    "fixtures/anti-patterns/mutation-evidence-umbrella.invalid.json",
    "tools/validate_mutation_evidence_accountability.py",
]

IMPLEMENTATION_REPOS = [
    "SourceOS-Linux/BearBrowser",
    "SourceOS-Linux/TurtleTerm",
    "SourceOS-Linux/sourceos-shell",
    "SourceOS-Linux/sourceos-syncd",
    "SourceOS-Linux/sourceos-devtools",
    "SourceOS-Linux/sourceos-boot",
    "SocioProphet/prophet-platform",
    "SocioProphet/ontogenesis",
    "SocioProphet/exodus",
]

GUARDRAILS = [
    "no clearance when sensors are blind, degraded, or missing",
    "no extension-primary browser attribution when extension inventory is none_visible",
    "no delegated mutation without a complete actor chain",
    "no archive extraction without path-boundary and cleanup accounting",
    "no diagnostic observer-effect clearance with partial or redacted evidence",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _spec_root(args) -> pathlib.Path:
    return pathlib.Path(args.spec_root).expanduser().resolve()


def _print_checks(checks: list[Check]) -> int:
    rc = 0
    for check in checks:
        marker = {"pass": "ok", "fail": "fail", "warn": "warn"}.get(check.status, check.status)
        print(f"[{marker}] {check.name}: {check.detail}")
        if check.status == "fail":
            rc = 1
    return rc


def _collect_spec_checks(spec_root: pathlib.Path) -> list[Check]:
    checks = [
        Check(
            "spec-root",
            "pass" if spec_root.exists() and spec_root.is_dir() else "fail",
            str(spec_root),
        )
    ]
    for rel in REQUIRED_SPEC_PATHS:
        path = spec_root / rel
        checks.append(Check(rel, "pass" if path.exists() else "fail", str(path)))
    return checks


def plan(args) -> int:
    """Render the mutation/evidence devtools integration posture."""
    spec_root = _spec_root(args)
    print("SourceOS Mutation and Evidence Accountability devtools plan")
    print(f"spec_root: {spec_root}")
    print("canonical_spec_pr: https://github.com/SourceOS-Linux/sourceos-spec/pull/96")
    print("\nrequired spec files:")
    for rel in REQUIRED_SPEC_PATHS:
        print(f"- {rel}")
    print("\nimplementation repos:")
    for repo in IMPLEMENTATION_REPOS:
        print(f"- {repo}")
    print("\nsemantic guardrails:")
    for guardrail in GUARDRAILS:
        print(f"- {guardrail}")
    return 0


def inspect(args) -> int:
    """Inspect whether a sourceos-spec checkout has the mutation/evidence contract."""
    return _print_checks(_collect_spec_checks(_spec_root(args)))


def validate(args) -> int:
    """Run the canonical sourceos-spec mutation/evidence validator."""
    spec_root = _spec_root(args)
    checks = _collect_spec_checks(spec_root)
    check_rc = _print_checks(checks)
    if check_rc != 0:
        print("mutation/evidence validation skipped: required spec files are missing")
        return check_rc

    validator = spec_root / "tools" / "validate_mutation_evidence_accountability.py"
    cmd = [sys.executable, str(validator)]
    print(f"running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(spec_root), check=False, text=True)
    return int(result.returncode)


def fixture_plan(args) -> int:
    """Print the fixture classes expected by downstream implementation repos."""
    fixture_classes = {
        "valid": [
            "browser write with no visible extensions",
            "delegated sync chain with origin/requesting/execution/storage actors",
            "terminal/archive extraction with path-boundary and cleanup accounting",
            "diagnostic self-noise with clearance disabled when evidence is partial",
        ],
        "invalid": [
            "extension-primary browser write with extension_inventory_state=none_visible",
            "delegated mutation without complete actor chain",
            "diagnostic observer-effect receipt that allows clearance despite redaction",
            "archive extraction with unknown path class or missing cleanup policy",
        ],
    }
    print(json.dumps(fixture_classes, indent=2, sort_keys=True))
    return 0
