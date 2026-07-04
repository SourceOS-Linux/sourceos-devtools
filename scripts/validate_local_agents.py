#!/usr/bin/env python3
"""Validate SourceOS local-agent registry declarations."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationFinding:
    path: str
    field: str
    severity: str
    message: str


def _get(payload: dict[str, Any], dotted: str) -> Any:
    cursor: Any = payload
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def validate_payload(path: pathlib.Path, payload: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    required = [
        "schemaVersion",
        "name",
        "label",
        "scope",
        "runtime",
        "owner.project",
        "owner.component",
        "owner.contact",
        "container.name",
        "container.runtimeImage",
        "container.sourceImage",
        "container.pullPolicy",
        "podman.connection",
        "auth.mode",
        "auth.authfile",
        "auth.allowAmbientDockerConfig",
        "auth.allowInteractiveCredentialHelper",
        "macos.launchd.plist",
        "macos.launchd.legacySystemPlist",
        "macos.launchd.runAtLoad",
        "macos.launchd.keepAlive",
        "linux.systemdUserUnit",
        "logs.directory",
        "logs.app",
        "health.type",
        "health.expected",
    ]
    for field in required:
        if _get(payload, field) is None:
            findings.append(ValidationFinding(str(path), field, "high", "required field missing"))

    if payload.get("schemaVersion") != "sourceos.local-agent.v1":
        findings.append(ValidationFinding(str(path), "schemaVersion", "high", "unsupported schemaVersion"))

    if payload.get("scope") not in {"user", "system"}:
        findings.append(ValidationFinding(str(path), "scope", "high", "scope must be user or system"))

    if payload.get("runtime") not in {"podman", "native", "nix-app", "systemd"}:
        findings.append(ValidationFinding(str(path), "runtime", "high", "unsupported runtime"))

    runtime_image = _get(payload, "container.runtimeImage")
    if isinstance(runtime_image, str) and not runtime_image.startswith("localhost/"):
        findings.append(ValidationFinding(str(path), "container.runtimeImage", "high", "runtime image must use localhost tag"))

    pull_policy = _get(payload, "container.pullPolicy")
    if pull_policy not in {"never", "explicit", "always"}:
        findings.append(ValidationFinding(str(path), "container.pullPolicy", "high", "invalid pull policy"))

    auth_mode = _get(payload, "auth.mode")
    if auth_mode not in {"empty-authfile", "service-account", "none", "forbidden-ambient"}:
        findings.append(ValidationFinding(str(path), "auth.mode", "high", "invalid auth mode"))

    if _get(payload, "auth.allowAmbientDockerConfig") is not False:
        findings.append(ValidationFinding(str(path), "auth.allowAmbientDockerConfig", "high", "ambient Docker config must be disabled by default"))

    if _get(payload, "auth.allowInteractiveCredentialHelper") is not False:
        findings.append(ValidationFinding(str(path), "auth.allowInteractiveCredentialHelper", "high", "interactive credential helpers must be disabled"))

    if _get(payload, "macos.launchd.keepAlive") is True:
        findings.append(ValidationFinding(str(path), "macos.launchd.keepAlive", "high", "KeepAlive=true requires separate bounded restart policy review"))

    plist = _get(payload, "macos.launchd.plist")
    if isinstance(plist, str) and plist.startswith("/Library/LaunchAgents/"):
        findings.append(ValidationFinding(str(path), "macos.launchd.plist", "high", "user agents must not install under /Library/LaunchAgents"))

    logs = [_get(payload, "logs.directory"), _get(payload, "logs.app")]
    for field, value in zip(["logs.directory", "logs.app"], logs):
        if isinstance(value, str) and value.startswith("/tmp/"):
            findings.append(ValidationFinding(str(path), field, "high", "product logs must not use /tmp"))

    return findings


def iter_registry_files(root: pathlib.Path) -> list[pathlib.Path]:
    registry = root / "sourceosctl" / "local_agents"
    if not registry.exists():
        return []
    return sorted(p for p in registry.glob("*.json") if p.name != "schema.json")


def validate(root: pathlib.Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    files = iter_registry_files(root)
    if not files:
        return [ValidationFinding(str(root), "registry", "high", "no local-agent registry files found")]
    for path in files:
        try:
            payload = json.loads(path.read_text())
        except Exception as exc:
            findings.append(ValidationFinding(str(path), "json", "high", f"invalid JSON: {exc}"))
            continue
        if not isinstance(payload, dict):
            findings.append(ValidationFinding(str(path), "json", "high", "registry file must contain object"))
            continue
        findings.extend(validate_payload(path, payload))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SourceOS local-agent registry declarations")
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", default=False, help="Emit findings as JSON")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    findings = validate(root)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2, sort_keys=True))
    elif findings:
        print(f"local-agent registry validation: {len(findings)} finding(s)")
        for finding in findings:
            print(f"[{finding.severity}] {finding.path} {finding.field}: {finding.message}")
    else:
        print("local-agent registry validation: ok")
    return 1 if any(f.severity == "high" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
