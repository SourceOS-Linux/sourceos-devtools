"""agent-machine command helpers.

This module implements SourceOS Agent Machine local mount planning and the first
small guarded materialization slice.  It does not create Podman machines,
containers, or bind mounts.  It may create explicitly-scoped local output
folders only when called with --execute --policy-ok.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_DEV_ROOT = "~/dev"
DEFAULT_DOCS_ROOT = "~/Documents/SourceOS/agent-output"
DEFAULT_DOWNLOADS_ROOT = "~/Downloads/SourceOS/agent-downloads"

DEFAULT_DEV_AGENT_PATH = "/workspace/dev"
DEFAULT_DOCS_AGENT_PATH = "/workspace/output"
DEFAULT_DOWNLOADS_AGENT_PATH = "/workspace/downloads"

LOCAL_DATA_PLANE_REF = "urn:srcos:agent-machine-local-data-plane:local-default"
MOUNT_POLICY_REF = "urn:srcos:agent-machine-mount-policy:default-deny-scoped-roots"
WORKSPACE_ID = "urn:srcos:agent-machine-workspace:local-default"

SENSITIVE_PATTERNS = [
    "$HOME",
    "~/.ssh",
    "~/.gnupg",
    "~/Library/Keychains",
    "~/Library/Application Support/Google/Chrome",
    "~/Library/Application Support/Firefox",
    "~/.aws",
    "~/.config/gcloud",
    "~/.azure",
    "~/.kube",
    "~/.docker",
    "~/.npmrc",
    "~/.pypirc",
]


def _host_adapter() -> str:
    """Return the SourceOS host adapter name for the current platform."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return "linux"


def _storage_backend(host_adapter: str) -> str:
    """Return the default local storage backend for the host adapter."""
    if host_adapter == "macos":
        return "podman-machine-bind"
    if host_adapter == "windows":
        return "wsl-bind"
    return "native-bind"


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _home() -> str:
    return str(Path.home())


def _redact_home(path: str) -> str:
    """Redact the concrete home path when printing evidence-like output."""
    home = _home()
    expanded = _expand(path)
    if expanded == home:
        return "$HOME"
    if expanded.startswith(home + os.sep):
        return "$HOME" + expanded[len(home) :]
    return expanded


def _path_exists(path: str) -> bool:
    return Path(_expand(path)).exists()


def _policy_hash(payload: Dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def _is_whole_home(path: str) -> bool:
    return _expand(path) == _home()


def _is_unscoped_downloads(path: str) -> bool:
    return _expand(path) == _expand("~/Downloads")


def _validate_mount_plan(plan: Dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for mount in plan["mounts"]:
        host_path = mount["hostPath"]
        if _is_whole_home(host_path):
            errors.append(f"{mount['mountId']}: whole-home mount is forbidden: {mount['resolvedHostPath']}")
        if mount["pathClass"] == "downloads" and _is_unscoped_downloads(host_path):
            errors.append("browser-downloads: use ~/Downloads/SourceOS/agent-downloads, not ~/Downloads")
        redacted = mount["resolvedHostPath"]
        for sensitive in [".ssh", ".gnupg", "Keychains", ".aws", ".config/gcloud", ".azure", ".kube"]:
            if sensitive in redacted:
                errors.append(f"{mount['mountId']}: sensitive host path denied: {redacted}")
    return errors


def _mount(
    mount_id: str,
    path_class: str,
    host_path: str,
    agent_path: str,
    access_mode: str,
    default_for: Iterable[str],
    create_if_missing: bool,
    direct_execution_allowed: bool,
    description: str,
) -> Dict[str, Any]:
    return {
        "mountId": mount_id,
        "pathClass": path_class,
        "hostPath": host_path,
        "resolvedHostPath": _redact_home(host_path),
        "agentPath": agent_path,
        "accessMode": access_mode,
        "defaultFor": list(default_for),
        "secretsProhibited": True,
        "directExecutionAllowed": direct_execution_allowed,
        "createIfMissing": create_if_missing,
        "exists": _path_exists(host_path),
        "description": description,
    }


def _build_mount_plan(args) -> Dict[str, Any]:
    host_adapter = _host_adapter()
    dev_root = getattr(args, "dev_root", None) or DEFAULT_DEV_ROOT
    docs_root = getattr(args, "docs_root", None) or DEFAULT_DOCS_ROOT
    downloads_root = getattr(args, "downloads_root", None) or DEFAULT_DOWNLOADS_ROOT
    profile = getattr(args, "profile", None) or "macos-podman"

    plan = {
        "type": "AgentMachineMountPlan",
        "specVersion": "0.1.0",
        "profile": profile,
        "hostAdapter": host_adapter,
        "storageBackend": _storage_backend(host_adapter),
        "contractRefs": {
            "localDataPlaneSchema": "https://schemas.srcos.ai/v2/AgentMachineLocalDataPlane.json",
            "mountPolicySchema": "https://schemas.srcos.ai/v2/AgentMachineMountPolicy.json",
            "topolvmPlacementSchema": "https://schemas.srcos.ai/v2/TopoLVMPlacementProfile.json",
        },
        "mounts": [
            _mount(
                "dev-root",
                "code",
                dev_root,
                DEFAULT_DEV_AGENT_PATH,
                "read-write",
                ["agent", "editor", "terminal", "openclaw", "hermes", "codex", "claude-code"],
                False,
                True,
                "Explicit code/repository workspace root. This is not a whole-home mount.",
            ),
            _mount(
                "docs-output",
                "documents",
                docs_root,
                DEFAULT_DOCS_AGENT_PATH,
                "read-write",
                ["agent", "editor", "terminal", "openclaw", "hermes", "codex", "claude-code"],
                True,
                False,
                "Generated document/report output root for agent-authored files.",
            ),
            _mount(
                "browser-downloads",
                "downloads",
                downloads_root,
                DEFAULT_DOWNLOADS_AGENT_PATH,
                "browser-read-write-agent-read-only",
                ["browser"],
                True,
                False,
                "Scoped browser downloads root. The full host Downloads directory is intentionally not mounted.",
            ),
        ],
        "deniedPatterns": SENSITIVE_PATTERNS,
        "downloadPolicy": {
            "mountWholeDownloadsDirectoryAllowed": False,
            "hashDownloads": True,
            "agentAccess": "read-only",
            "browserAccess": "read-write",
            "directExecutionAllowed": False,
            "promotionRequiresEvidence": True,
        },
        "evidence": {
            "required": True,
            "recordMountLaunch": True,
            "recordDeniedAttempts": True,
            "recordHostPath": True,
            "redactHostUserName": True,
        },
        "dryRun": True,
    }
    plan["policyHash"] = _policy_hash({"mounts": plan["mounts"], "deniedPatterns": plan["deniedPatterns"]})
    return plan


def _build_mount_evidence(plan: Dict[str, Any], created: list[str], denied: list[str]) -> Dict[str, Any]:
    return {
        "kind": "AgentMachineMountEvidence",
        "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "workspaceId": WORKSPACE_ID,
        "bundle": None,
        "executor": "sourceosctl-local",
        "backendIntent": "agent-machine",
        "localDataPlaneRef": LOCAL_DATA_PLANE_REF,
        "mountPolicyRef": MOUNT_POLICY_REF,
        "secureHostInterfaceRef": None,
        "topolvmPlacementProfileRef": None,
        "storageBackend": plan["storageBackend"],
        "policyHash": plan["policyHash"],
        "gitRef": None,
        "mounts": [
            {
                "mountId": m["mountId"],
                "pathClass": m["pathClass"],
                "hostPathRef": m["resolvedHostPath"],
                "agentPath": m["agentPath"],
                "accessMode": m["accessMode"],
                "storageBackend": plan["storageBackend"],
                "gitRef": None,
                "contentHash": None,
                "secretsProhibited": m["secretsProhibited"],
                "directExecutionAllowed": m["directExecutionAllowed"],
                "existsAtRunStart": m["exists"],
            }
            for m in plan["mounts"]
        ],
        "deniedAttempts": [
            {"pathRef": item, "reason": "Denied by Agent Machine mount policy", "severity": "deny"}
            for item in denied
        ],
        "downloadArtifacts": [],
        "topolvmPlacement": None,
        "redactionSummary": {
            "hostUserRedacted": True,
            "secretLikeValuesRedacted": 0,
            "notes": "sourceosctl local guarded materialization evidence",
        },
        "createdHostPaths": created,
    }


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    target = Path(_expand(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def mounts_plan(args) -> int:
    """Render a dry-run mount plan for an Agent Machine profile."""
    plan = _build_mount_plan(args)
    errors = _validate_mount_plan(plan)
    if errors:
        plan["policyErrors"] = errors
    return _print_json(plan)


def mounts_init(args) -> int:
    """Render or execute guarded initialization for scoped local directories.

    Execution creates only declared, create-if-missing local directories such as
    the docs output root and scoped browser downloads root. It does not mount
    Podman volumes or create containers.
    """
    execute = bool(getattr(args, "execute", False))
    policy_ok = bool(getattr(args, "policy_ok", False))

    plan = _build_mount_plan(args)
    plan["operation"] = "init"
    errors = _validate_mount_plan(plan)
    if errors:
        plan["policyErrors"] = errors
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 1

    would_create = [
        m
        for m in plan["mounts"]
        if m.get("createIfMissing") and not m.get("exists")
    ]
    plan["wouldCreate"] = [m["resolvedHostPath"] for m in would_create]

    if not execute:
        return _print_json(plan)

    if not policy_ok:
        print("error: --execute requires --policy-ok for mount initialization", file=sys.stderr)
        return 1

    created: list[str] = []
    for mount in would_create:
        Path(_expand(mount["hostPath"])).mkdir(parents=True, exist_ok=True)
        created.append(mount["resolvedHostPath"])

    evidence = _build_mount_evidence(plan, created=created, denied=[])
    evidence_out = getattr(args, "evidence_out", None)
    if evidence_out:
        _write_json(evidence_out, evidence)

    result = {
        "type": "AgentMachineMountInitResult",
        "executed": True,
        "created": created,
        "evidenceOut": _redact_home(evidence_out) if evidence_out else None,
        "evidence": evidence if not evidence_out else None,
    }
    return _print_json(result)


def mounts_inspect(args) -> int:
    """Inspect the default/local Agent Machine mount posture."""
    plan = _build_mount_plan(args)
    include_downloads = getattr(args, "include_downloads", False)
    if not include_downloads:
        plan["mounts"] = [m for m in plan["mounts"] if m["pathClass"] != "downloads"]
    plan["operation"] = "inspect"
    return _print_json(plan)


def mounts_evidence_inspect(args) -> int:
    """Inspect a mount evidence JSON file."""
    path = Path(args.path)
    if not path.exists():
        print(f"error: evidence file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    kind = payload.get("kind") or payload.get("type")
    summary = {
        "path": str(path),
        "kind": kind,
        "workspaceId": payload.get("workspaceId"),
        "policyHash": payload.get("policyHash"),
        "mountCount": len(payload.get("mounts", [])) if isinstance(payload.get("mounts"), list) else 0,
        "hasDownloads": any(
            m.get("pathClass") == "downloads"
            for m in payload.get("mounts", [])
            if isinstance(m, dict)
        )
        if isinstance(payload.get("mounts", []), list)
        else False,
    }
    return _print_json(summary)
