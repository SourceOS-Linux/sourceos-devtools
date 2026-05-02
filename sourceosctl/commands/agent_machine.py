"""agent-machine command helpers.

This module implements the first dry-run/read-only slice of the SourceOS
Agent Machine local mount surface.  It does not create Podman machines, create
containers, or mutate host mounts.  It renders and inspects the mount contract
that later commands will apply under policy.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_DEV_ROOT = "~/dev"
DEFAULT_DOCS_ROOT = "~/Documents/SourceOS/agent-output"
DEFAULT_DOWNLOADS_ROOT = "~/Downloads/SourceOS/agent-downloads"

DEFAULT_DEV_AGENT_PATH = "/workspace/dev"
DEFAULT_DOCS_AGENT_PATH = "/workspace/output"
DEFAULT_DOWNLOADS_AGENT_PATH = "/workspace/downloads"

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


def _redact_home(path: str) -> str:
    """Redact the concrete home path when printing evidence-like output."""
    home = str(Path.home())
    expanded = _expand(path)
    if expanded == home:
        return "$HOME"
    if expanded.startswith(home + os.sep):
        return "$HOME" + expanded[len(home) :]
    return expanded


def _path_exists(path: str) -> bool:
    return Path(_expand(path)).exists()


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

    return {
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


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def mounts_plan(args) -> int:
    """Render a dry-run mount plan for an Agent Machine profile."""
    return _print_json(_build_mount_plan(args))


def mounts_init(args) -> int:
    """Render the mount initialization plan.

    The current implementation remains dry-run only.  It tells the operator
    which directories would be created and which mounts would be declared.
    """
    if not getattr(args, "dry_run", True):
        print(
            "error: mount initialization is dry-run only in this release",
            file=sys.stderr,
        )
        return 1

    plan = _build_mount_plan(args)
    plan["operation"] = "init"
    plan["wouldCreate"] = [
        m["resolvedHostPath"]
        for m in plan["mounts"]
        if m.get("createIfMissing") and not m.get("exists")
    ]
    return _print_json(plan)


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

    summary = {
        "path": str(path),
        "type": payload.get("type"),
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
