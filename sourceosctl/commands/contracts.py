"""SourceOS contract validation and estate scanning helpers.

The M1 implementation is intentionally local-only and dependency-light. It
validates JSON shape and the minimum SourceOS repo manifest contract until the
full schema mirror from SourceOS-Linux/sourceos-spec is vendored or fetched by a
future hardened validator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


REQUIRED_REPO_MANIFEST_FIELDS = [
    "repo",
    "domain",
    "specVersion",
    "ownedSchemas",
    "syncEngines",
    "sourceChannels",
    "policyClasses",
    "auditEvents",
    "dangerousSurfaces",
]

VALID_DOMAINS = {
    "spec",
    "tooling",
    "workspace",
    "agent",
    "policy",
    "memory",
    "shell",
    "browser",
    "os",
    "transport",
    "observability",
    "model",
    "security",
    "integration",
}

VALID_POLICY_CLASSES = {"low", "medium", "high", "critical"}


def _load_json(path: Path) -> Tuple[Dict[str, Any] | None, List[str]]:
    if not path.exists():
        return None, [f"missing file: {path}"]
    if not path.is_file():
        return None, [f"not a file: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["top-level JSON value must be an object"]
    return payload, []


def validate_repo_manifest(payload: Dict[str, Any]) -> List[str]:
    """Return validation errors for a SourceOSRepoManifest-like payload."""
    errors: List[str] = []
    for field in REQUIRED_REPO_MANIFEST_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    repo = payload.get("repo")
    if repo is not None and (not isinstance(repo, str) or "/" not in repo):
        errors.append("repo must be a GitHub owner/name string")

    domain = payload.get("domain")
    if domain is not None and domain not in VALID_DOMAINS:
        errors.append(f"domain must be one of: {', '.join(sorted(VALID_DOMAINS))}")

    for list_field in [
        "ownedSchemas",
        "syncEngines",
        "sourceChannels",
        "policyClasses",
        "auditEvents",
        "dangerousSurfaces",
    ]:
        value = payload.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"{list_field} must be an array")

    policy_classes = payload.get("policyClasses")
    if isinstance(policy_classes, list):
        for policy_class in policy_classes:
            if policy_class not in VALID_POLICY_CLASSES:
                errors.append(f"invalid policy class: {policy_class}")

    sync_engines = payload.get("syncEngines")
    if isinstance(sync_engines, list):
        for index, engine in enumerate(sync_engines):
            if not isinstance(engine, dict):
                errors.append(f"syncEngines[{index}] must be an object")
                continue
            for field in ["engineId", "collection", "ownerRepo", "policyClass", "mergeStrategy"]:
                if field not in engine:
                    errors.append(f"syncEngines[{index}] missing {field}")

    return errors


def _classify_manifest(path: Path) -> Dict[str, Any]:
    payload, errors = _load_json(path)
    if payload is None:
        return {"path": str(path), "status": "missing-manifest", "errors": errors}
    errors.extend(validate_repo_manifest(payload))
    status = "compliant" if not errors else "invalid-manifest"
    return {
        "path": str(path),
        "repo": payload.get("repo"),
        "domain": payload.get("domain"),
        "status": status,
        "errors": errors,
    }


def contract_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    payload, errors = _load_json(path)
    if payload is not None and (path.name == "manifest.json" or "repo" in payload):
        errors.extend(validate_repo_manifest(payload))

    result = {
        "path": str(path),
        "status": "valid" if not errors else "invalid",
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status'].upper()}: {path}")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


def repo_scan(args: argparse.Namespace) -> int:
    root = Path(args.path)
    manifest = root / ".sourceos" / "manifest.json"
    result = _classify_manifest(manifest)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {root}")
        if result.get("repo"):
            print(f"repo: {result['repo']}")
        if result.get("domain"):
            print(f"domain: {result['domain']}")
        for error in result.get("errors", []):
            print(f"- {error}")
    return 0 if result["status"] == "compliant" else 1


def _candidate_repos(root: Path) -> Iterable[Path]:
    if (root / ".sourceos" / "manifest.json").exists():
        yield root
    for child in sorted(root.iterdir()) if root.exists() and root.is_dir() else []:
        if child.is_dir() and (child / ".sourceos" / "manifest.json").exists():
            yield child


def estate_scan(args: argparse.Namespace) -> int:
    root = Path(args.path)
    results = [_classify_manifest(repo / ".sourceos" / "manifest.json") for repo in _candidate_repos(root)]
    missing = not results
    if args.json:
        print(json.dumps({"root": str(root), "results": results}, indent=2, sort_keys=True))
    else:
        if missing:
            print(f"missing-manifest: no .sourceos/manifest.json files found under {root}")
        for result in results:
            print(f"{result['status']}: {result.get('repo') or result['path']}")
            for error in result.get("errors", []):
                print(f"  - {error}")
    return 1 if missing or any(r["status"] != "compliant" for r in results) else 0


def graph_doctor(args: argparse.Namespace) -> int:
    print("SourceGraph doctor: contract surface present; runtime graph backend not configured in sourceos-devtools.")
    print("Expected contracts: SourceGraphWrite, AuditEvent, PolicyDecision, AgentCapabilityLease.")
    return 0


def sync_doctor(args: argparse.Namespace) -> int:
    print("SourceSync doctor: local manifest validation available; relay/sync runtime checks are not configured here.")
    print("Expected contracts: SourceOSRepoManifest and SyncEngineManifest.")
    return 0


def policy_explain(args: argparse.Namespace) -> int:
    payload, errors = _load_json(Path(args.path))
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    decision = payload.get("decision") or payload.get("outcome") or "unknown"
    reason = payload.get("reasonCode") or payload.get("decisionHash") or "no reasonCode/decisionHash present"
    print(f"decision: {decision}")
    print(f"reason: {reason}")
    if payload.get("policyId"):
        print(f"policy: {payload['policyId']}")
    if payload.get("policyDomain"):
        print(f"policyDomain: {payload['policyDomain']}")
    return 0


def build_contract_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl contract", description="SourceOS contract helpers")
    sub = parser.add_subparsers(dest="contract_command", metavar="<subcommand>")
    sub.required = True
    validate_p = sub.add_parser("validate", help="Validate a JSON contract file")
    validate_p.add_argument("path")
    validate_p.add_argument("--json", action="store_true", default=False)
    validate_p.set_defaults(func=contract_validate)
    return parser


def contract_main(argv: List[str] | None = None) -> int:
    parser = build_contract_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


def build_repo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl repo", description="SourceOS repo helpers")
    sub = parser.add_subparsers(dest="repo_command", metavar="<subcommand>")
    sub.required = True
    scan_p = sub.add_parser("scan", help="Scan one repo for .sourceos/manifest.json")
    scan_p.add_argument("path")
    scan_p.add_argument("--json", action="store_true", default=False)
    scan_p.set_defaults(func=repo_scan)
    return parser


def repo_main(argv: List[str] | None = None) -> int:
    parser = build_repo_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


def build_estate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl estate", description="SourceOS estate helpers")
    sub = parser.add_subparsers(dest="estate_command", metavar="<subcommand>")
    sub.required = True
    scan_p = sub.add_parser("scan", help="Scan child repos for .sourceos/manifest.json")
    scan_p.add_argument("path", nargs="?", default=".")
    scan_p.add_argument("--json", action="store_true", default=False)
    scan_p.set_defaults(func=estate_scan)
    return parser


def estate_main(argv: List[str] | None = None) -> int:
    parser = build_estate_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


def graph_main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sourceosctl graph", description="SourceGraph helpers")
    sub = parser.add_subparsers(dest="graph_command", metavar="<subcommand>")
    sub.required = True
    doctor_p = sub.add_parser("doctor", help="Inspect SourceGraph contract posture")
    doctor_p.set_defaults(func=graph_doctor)
    args = parser.parse_args(argv)
    return args.func(args) or 0


def sync_main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sourceosctl sync", description="SourceSync helpers")
    sub = parser.add_subparsers(dest="sync_command", metavar="<subcommand>")
    sub.required = True
    doctor_p = sub.add_parser("doctor", help="Inspect SourceSync contract posture")
    doctor_p.set_defaults(func=sync_doctor)
    args = parser.parse_args(argv)
    return args.func(args) or 0


def policy_main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sourceosctl policy", description="SourcePolicy helpers")
    sub = parser.add_subparsers(dest="policy_command", metavar="<subcommand>")
    sub.required = True
    explain_p = sub.add_parser("explain", help="Explain a PolicyDecision/AuditEvent JSON file")
    explain_p.add_argument("path")
    explain_p.set_defaults(func=policy_explain)
    args = parser.parse_args(argv)
    return args.func(args) or 0
