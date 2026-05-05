#!/usr/bin/env python3
"""Validate SourceOS local-agent backend templates."""

from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    path: str
    severity: str
    message: str


REQUIRED_SYSTEMD_SNIPPETS = [
    "Restart={{restart}}",
    "RestartSec={{restart_sec}}",
    "StartLimitIntervalSec={{start_limit_interval_sec}}",
    "StartLimitBurst={{start_limit_burst}}",
    "Environment=CONTAINERS_AUTH_FILE={{authfile}}",
]

REQUIRED_QUADLET_SNIPPETS = [
    "Pull=never",
    "AuthFile={{authfile}}",
    "AutoUpdate=registry-disabled",
    "Restart={{restart}}",
    "StartLimitIntervalSec={{start_limit_interval_sec}}",
    "StartLimitBurst={{start_limit_burst}}",
]

FORBIDDEN_SNIPPETS = [
    "Restart=always",
    "Pull=always",
    "AutoUpdate=registry",
    "/tmp/",
]


def validate_template(path: pathlib.Path) -> list[Finding]:
    text = path.read_text(errors="replace")
    findings: list[Finding] = []
    required = REQUIRED_QUADLET_SNIPPETS if path.name.endswith(".container.tmpl") else REQUIRED_SYSTEMD_SNIPPETS
    for snippet in required:
        if snippet not in text:
            findings.append(Finding(str(path), "high", f"missing required snippet: {snippet}"))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            findings.append(Finding(str(path), "high", f"forbidden snippet: {snippet}"))
    return findings


def validate(root: pathlib.Path) -> list[Finding]:
    template_dir = root / "sourceosctl" / "local_agents" / "templates"
    if not template_dir.exists():
        return [Finding(str(template_dir), "high", "template directory missing")]
    templates = sorted(template_dir.glob("*.tmpl"))
    if not templates:
        return [Finding(str(template_dir), "high", "no templates found")]
    findings: list[Finding] = []
    for path in templates:
        findings.extend(validate_template(path))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SourceOS local-agent backend templates")
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    args = parser.parse_args(argv)
    findings = validate(pathlib.Path(args.root).resolve())
    if not findings:
        print("local-agent template validation: ok")
        return 0
    print(f"local-agent template validation: {len(findings)} finding(s)")
    for finding in findings:
        print(f"[{finding.severity}] {finding.path}: {finding.message}")
    return 1 if any(f.severity == "high" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
