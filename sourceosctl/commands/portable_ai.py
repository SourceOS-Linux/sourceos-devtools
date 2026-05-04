"""Portable AI Kit helpers.

This module renders portable-AI preflight, profile, prepare, and launch plans.
It does not download model weights, start daemons, run inference, or write outside
an explicitly-approved portable root.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Dict


PORTABLE_LAYOUT_VERSION = "sourceos.portable-ai/v1alpha1"

PORTABLE_PROFILES: dict[str, dict[str, Any]] = {
    "tiny-router": {
        "displayName": "Tiny Router Kit",
        "minimumFreeGb": 8,
        "recommendedFreeGb": 16,
        "roles": ["router", "triage", "rewrite", "summarization"],
        "surfaces": ["turtleterm", "agent-term", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "deny"},
    },
    "laptop-safe": {
        "displayName": "Laptop-safe Portable AI Kit",
        "minimumFreeGb": 16,
        "recommendedFreeGb": 32,
        "roles": ["offline-fallback", "office-assist", "privacy-first-chat", "rewrite"],
        "surfaces": ["turtleterm", "bearbrowser", "agent-term", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "deny"},
    },
    "office-local": {
        "displayName": "Office-local Portable AI Kit",
        "minimumFreeGb": 32,
        "recommendedFreeGb": 64,
        "roles": ["office-assist", "summarization", "artifact-drafting", "workroom-local"],
        "surfaces": ["bearbrowser", "turtleterm", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "workroom-scoped"},
    },
    "code-local": {
        "displayName": "Code-local Portable AI Kit",
        "minimumFreeGb": 32,
        "recommendedFreeGb": 64,
        "roles": ["coding-assist", "repo-triage", "rewrite", "summarization"],
        "surfaces": ["turtleterm", "agent-term", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "repo-scoped"},
    },
    "field-kit": {
        "displayName": "Field Operator Portable AI Kit",
        "minimumFreeGb": 64,
        "recommendedFreeGb": 128,
        "roles": ["offline-fallback", "operator-assist", "evidence-inspection", "field-workroom"],
        "surfaces": ["turtleterm", "agent-term", "bearbrowser", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "evidence-scoped"},
    },
    "byom-gguf": {
        "displayName": "Bring-your-own GGUF Portable Kit",
        "minimumFreeGb": 8,
        "recommendedFreeGb": 64,
        "roles": ["operator-selected"],
        "surfaces": ["turtleterm", "agent-term", "local-web"],
        "policy": {"promptEgressDefault": "deny", "toolUseDefault": "deny", "hostWritesDefault": "deny", "requiresHashBeforeEligibility": True},
    },
}

PORTABLE_DIRS = [
    "manifests",
    "runtimes/ollama",
    "runtimes/llama-cpp",
    "runtimes/openai-compatible-local",
    "models/blobs",
    "models/modelfiles",
    "cache/embeddings",
    "cache/retrieval",
    "cache/prompt-prefix",
    "state/chat",
    "state/workrooms",
    "state/routes",
    "surfaces/turtleterm",
    "surfaces/agent-term",
    "surfaces/bearbrowser",
    "evidence/preflight",
    "evidence/materialization",
    "evidence/activation",
    "evidence/wipe",
    "tmp",
]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _target(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _disk_usage_gb(path: Path) -> dict[str, float | None]:
    probe = path if path.exists() else path.parent
    try:
        total, used, free = shutil.disk_usage(probe)
    except FileNotFoundError:
        return {"totalGb": None, "usedGb": None, "freeGb": None}
    gb = 1024 ** 3
    return {
        "totalGb": round(total / gb, 2),
        "usedGb": round(used / gb, 2),
        "freeGb": round(free / gb, 2),
    }


def _writable(path: Path) -> bool:
    probe = path if path.exists() else path.parent
    return probe.exists() and os.access(probe, os.W_OK)


def _large_file_warning(path: Path) -> str | None:
    # Python's stdlib does not expose portable fs type for every platform.
    # Keep this conservative; Linux/macOS launchers can add richer fs probing.
    name = str(path).lower()
    if "fat32" in name or "vfat" in name:
        return "target path appears to reference FAT32/VFAT; GGUF files larger than 4GB may fail"
    return None


def _runtime_paths() -> dict[str, str | None]:
    return {
        "ollama": shutil.which("ollama"),
        "llama-cpp": shutil.which("llama-server") or shutil.which("llama.cpp"),
        "python3": shutil.which("python3"),
    }


def _profile(name: str) -> dict[str, Any]:
    try:
        return PORTABLE_PROFILES[name]
    except KeyError:
        known = ", ".join(sorted(PORTABLE_PROFILES))
        raise SystemExit(f"unknown portable AI profile: {name}; known profiles: {known}")


def profiles(args) -> int:
    return _print_json(
        {
            "type": "PortableAIProfiles",
            "apiVersion": PORTABLE_LAYOUT_VERSION,
            "profiles": PORTABLE_PROFILES,
            "policy": {
                "defaultMutability": "dry-run",
                "modelDownloads": "explicit-only",
                "promptEgressDefault": "deny",
                "hostWritesDefault": "deny",
            },
        }
    )


def preflight(args) -> int:
    target = _target(args.target_root)
    usage = _disk_usage_gb(target)
    warning = _large_file_warning(target)
    runtime_paths = _runtime_paths()
    exists = target.exists()
    writable = _writable(target)
    free_gb = usage.get("freeGb")
    failures: list[str] = []
    warnings: list[str] = []

    if not exists and not target.parent.exists():
        failures.append("target parent does not exist")
    if not writable:
        failures.append("target or parent is not writable")
    if warning:
        warnings.append(warning)
    if free_gb is not None and free_gb < 8:
        failures.append("less than 8GB free; no built-in portable profile can be prepared safely")
    elif free_gb is not None and free_gb < 16:
        warnings.append("less than 16GB free; only tiny-router or small BYOM profiles are realistic")

    decision = "fail" if failures else "warn" if warnings else "pass"

    return _print_json(
        {
            "type": "PortablePreflightEvidence",
            "apiVersion": PORTABLE_LAYOUT_VERSION,
            "capturedAt": _now(),
            "targetRoot": str(target),
            "exists": exists,
            "writable": writable,
            "disk": usage,
            "host": {
                "system": platform.system(),
                "machine": platform.machine(),
                "platform": platform.platform(),
            },
            "runtimePaths": runtime_paths,
            "benchmarkRequested": bool(getattr(args, "benchmark", False)),
            "benchmarkPerformed": False,
            "largeFileSupportWarning": warning,
            "failures": failures,
            "warnings": warnings,
            "decision": decision,
            "mutatesTarget": False,
        }
    )


def _portable_root_manifest(target: Path, profile_name: str) -> dict[str, Any]:
    profile = _profile(profile_name)
    return {
        "type": "PortableAIRoot",
        "apiVersion": PORTABLE_LAYOUT_VERSION,
        "id": f"urn:srcos:portable-ai-root:{target.name or 'portable-root'}",
        "createdAt": _now(),
        "targetRoot": str(target),
        "layoutVersion": PORTABLE_LAYOUT_VERSION,
        "profile": profile_name,
        "profileDisplayName": profile["displayName"],
        "directories": PORTABLE_DIRS,
        "surfaces": profile["surfaces"],
        "roles": profile["roles"],
        "policy": {
            **profile["policy"],
            "modelDownloads": "explicit-only",
            "runtimeActivation": "agent-machine-gated",
            "bindAddressDefault": "127.0.0.1",
            "evidenceRequired": True,
        },
    }


def prepare(args) -> int:
    target = _target(args.target_root)
    profile_name = args.profile
    profile = _profile(profile_name)
    manifest = _portable_root_manifest(target, profile_name)
    directories = [str(target / rel) for rel in PORTABLE_DIRS]

    if not getattr(args, "execute", False):
        return _print_json(
            {
                "type": "PortablePreparePlan",
                "apiVersion": PORTABLE_LAYOUT_VERSION,
                "capturedAt": _now(),
                "targetRoot": str(target),
                "profile": profile_name,
                "profileDetails": profile,
                "wouldCreateDirectories": directories,
                "wouldWriteManifest": str(target / "manifests" / "portable-ai-root.json"),
                "wouldWriteEvidence": bool(getattr(args, "evidence_out", None)),
                "wouldDownloadModels": False,
                "wouldStartRuntime": False,
                "requiresExecuteAndPolicyOk": True,
            }
        )

    if not getattr(args, "policy_ok", False):
        print("error: --execute requires --policy-ok for portable AI materialization", file=sys.stderr)
        return 2

    target.mkdir(parents=True, exist_ok=True)
    for rel in PORTABLE_DIRS:
        (target / rel).mkdir(parents=True, exist_ok=True)

    manifest_path = target / "manifests" / "portable-ai-root.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence = {
        "type": "PortableMaterializationEvidence",
        "apiVersion": PORTABLE_LAYOUT_VERSION,
        "capturedAt": _now(),
        "targetRoot": str(target),
        "profile": profile_name,
        "createdDirectories": directories,
        "manifestPath": str(manifest_path),
        "downloadedModels": False,
        "startedRuntime": False,
        "promptEgressDefault": "deny",
        "hostWritesDefault": profile["policy"].get("hostWritesDefault", "deny"),
    }
    if getattr(args, "evidence_out", None):
        Path(args.evidence_out).expanduser().write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return _print_json(evidence)


def start_plan(args) -> int:
    target = _target(args.target_root)
    surface = args.surface
    manifest_path = target / "manifests" / "portable-ai-root.json"
    manifest = None
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {"error": "portable-ai-root.json is not valid JSON"}

    return _print_json(
        {
            "type": "PortableAIStartPlan",
            "apiVersion": PORTABLE_LAYOUT_VERSION,
            "capturedAt": _now(),
            "targetRoot": str(target),
            "manifestPath": str(manifest_path),
            "manifestPresent": manifest_path.exists(),
            "manifest": manifest,
            "surface": surface,
            "runtimeProviderOrder": ["llama.cpp", "ollama-compatible", "openai-compatible-local"],
            "bindAddress": "127.0.0.1",
            "wouldStartRuntime": False,
            "requiresAgentMachineActivation": True,
            "requiresPolicyAdmission": True,
            "requiresAgentRegistryGrant": True,
            "promptEgressDefault": "deny",
            "hostWritesDefault": "deny",
            "routeDescriptorSecretFree": True,
        }
    )


def inspect(args) -> int:
    target = _target(args.target_root)
    paths = {rel: (target / rel).exists() for rel in PORTABLE_DIRS}
    manifest_path = target / "manifests" / "portable-ai-root.json"
    return _print_json(
        {
            "type": "PortableAIInspect",
            "apiVersion": PORTABLE_LAYOUT_VERSION,
            "capturedAt": _now(),
            "targetRoot": str(target),
            "exists": target.exists(),
            "manifestPath": str(manifest_path),
            "manifestPresent": manifest_path.exists(),
            "directories": paths,
            "disk": _disk_usage_gb(target),
        }
    )


def evidence_inspect(args) -> int:
    path = Path(args.path).expanduser()
    if not path.exists():
        print(f"error: evidence file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    return _print_json(
        {
            "path": str(path),
            "type": payload.get("type"),
            "apiVersion": payload.get("apiVersion"),
            "targetRoot": payload.get("targetRoot"),
            "decision": payload.get("decision"),
            "promptEgressDefault": payload.get("promptEgressDefault"),
            "hostWritesDefault": payload.get("hostWritesDefault"),
        }
    )
