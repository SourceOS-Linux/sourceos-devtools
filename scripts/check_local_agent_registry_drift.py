#!/usr/bin/env python3
"""Check for local-agent declaration drift.

The registry under sourceosctl/local_agents/*.json is the source of truth.
This checker prevents accidental divergence between registry declarations,
legacy CLI defaults, and generated runtime artifacts.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DriftFinding:
    severity: str
    subject: str
    message: str


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def _registry_files(root: pathlib.Path) -> list[pathlib.Path]:
    registry = root / "sourceosctl" / "local_agents"
    return sorted(p for p in registry.glob("*.json") if p.name != "schema.json")


def _read(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def check_registry(root: pathlib.Path) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    local_agent_py = _read(root / "sourceosctl" / "commands" / "local_agent.py")
    adapter_py = _read(root / "sourceosctl" / "commands" / "local_agent_registry_cli.py")
    scanner_py = _read(root / "scripts" / "scan_local_persistence.py")

    for path in _registry_files(root):
        payload = _load_json(path)
        name = payload.get("name")
        runtime_image = payload.get("container", {}).get("runtimeImage")
        source_image = payload.get("container", {}).get("sourceImage")
        label = payload.get("label")
        plist = payload.get("macos", {}).get("launchd", {}).get("plist")

        if not name:
            findings.append(DriftFinding("high", str(path), "missing name"))
            continue

        if name not in path.stem:
            findings.append(DriftFinding("medium", str(path), "file name should include agent name"))

        if runtime_image and runtime_image not in local_agent_py and runtime_image not in adapter_py:
            findings.append(DriftFinding("medium", str(path), "runtime image is not referenced by CLI implementation"))

        if source_image and source_image not in local_agent_py and source_image not in adapter_py:
            findings.append(DriftFinding("medium", str(path), "source image provenance is not referenced by CLI implementation"))

        if label and label not in local_agent_py and label not in adapter_py:
            findings.append(DriftFinding("medium", str(path), "service label is not referenced by CLI implementation"))

        if plist and plist.startswith("/Library/LaunchAgents/"):
            findings.append(DriftFinding("high", str(path), "registry plist points to system-wide LaunchAgents"))

    # Ensure the adapter remains the routed entrypoint path and the old module is not the only surface.
    sourceos_agent = _read(root / "bin" / "sourceos-agent")
    sourceosctl = _read(root / "bin" / "sourceosctl")
    if "local_agent_registry_cli" not in sourceos_agent:
        findings.append(DriftFinding("high", "bin/sourceos-agent", "entrypoint does not use registry-backed adapter"))
    if "local_agent_registry_cli" not in sourceosctl:
        findings.append(DriftFinding("high", "bin/sourceosctl", "sourceosctl local-agent route does not use registry-backed adapter"))
    if "RULES" not in scanner_py:
        findings.append(DriftFinding("medium", "scripts/scan_local_persistence.py", "scanner rule set not found"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check SourceOS local-agent registry drift")
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", default=False, help="Emit JSON")
    parser.add_argument("--fail-on", choices=["none", "medium", "high"], default="high", help="Failure threshold")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    findings = check_registry(root)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2, sort_keys=True))
    elif findings:
        print(f"local-agent registry drift: {len(findings)} finding(s)")
        for finding in findings:
            print(f"[{finding.severity}] {finding.subject}: {finding.message}")
    else:
        print("local-agent registry drift: ok")

    if args.fail_on == "none":
        return 0
    severities = {"medium": {"medium", "high"}, "high": {"high"}}[args.fail_on]
    return 1 if any(f.severity in severities for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
