from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path
from typing import Any

PORTABLE_LAYOUT_VERSION = "sourceos.portable-ai/v1alpha1"

PORTABLE_PROFILES: dict[str, dict[str, Any]] = {
    "tiny-router": {"displayName": "Tiny Router Kit", "minimumFreeGb": 8, "recommendedFreeGb": 16},
    "laptop-safe": {"displayName": "Laptop-safe Portable AI Kit", "minimumFreeGb": 16, "recommendedFreeGb": 32},
    "office-local": {"displayName": "Office-local Portable AI Kit", "minimumFreeGb": 32, "recommendedFreeGb": 64},
    "code-local": {"displayName": "Code-local Portable AI Kit", "minimumFreeGb": 32, "recommendedFreeGb": 64},
    "field-kit": {"displayName": "Field Operator Portable AI Kit", "minimumFreeGb": 64, "recommendedFreeGb": 128},
    "byom-gguf": {"displayName": "Bring-your-own GGUF Portable Kit", "minimumFreeGb": 8, "recommendedFreeGb": 64},
}

PORTABLE_DIRS = ["manifests", "models/blobs", "cache", "state/routes", "evidence/preflight", "evidence/materialization", "tmp"]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _print(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _disk(path: Path) -> dict[str, float | None]:
    probe = path if path.exists() else path.parent
    try:
        total, used, free = shutil.disk_usage(probe)
    except FileNotFoundError:
        return {"totalGb": None, "usedGb": None, "freeGb": None}
    gb = 1024 ** 3
    return {"totalGb": round(total / gb, 2), "usedGb": round(used / gb, 2), "freeGb": round(free / gb, 2)}


def profiles(_args) -> int:
    return _print({"type": "PortableAIProfiles", "apiVersion": PORTABLE_LAYOUT_VERSION, "profiles": PORTABLE_PROFILES})


def preflight(args) -> int:
    target = _root(args.target_root)
    profile_name = getattr(args, "profile", "laptop-safe")
    profile = PORTABLE_PROFILES[profile_name]
    disk = _disk(target)
    parent = target if target.exists() else target.parent
    writable = parent.exists() and os.access(parent, os.W_OK)
    failures: list[str] = []
    warnings: list[str] = []
    free_gb = disk.get("freeGb")
    if not writable:
        failures.append("target parent is not writable")
    if free_gb is not None and free_gb < profile["minimumFreeGb"]:
        failures.append("free space below profile minimum")
    elif free_gb is not None and free_gb < profile["recommendedFreeGb"]:
        warnings.append("free space below profile recommendation")
    return _print({
        "type": "PortablePreflightEvidence",
        "apiVersion": PORTABLE_LAYOUT_VERSION,
        "capturedAt": _now(),
        "targetRoot": str(target),
        "profile": profile_name,
        "disk": disk,
        "writable": writable,
        "failures": failures,
        "warnings": warnings,
        "decision": "fail" if failures else "warn" if warnings else "pass",
    })


def prepare(args) -> int:
    target = _root(args.target_root)
    profile_name = args.profile
    return _print({
        "type": "PortablePreparePlan",
        "apiVersion": PORTABLE_LAYOUT_VERSION,
        "capturedAt": _now(),
        "targetRoot": str(target),
        "profile": profile_name,
        "wouldCreateDirectories": [str(target / rel) for rel in PORTABLE_DIRS],
        "wouldWriteManifest": str(target / "manifests" / "portable-ai-root.json"),
        "wouldStartProvider": False,
        "wouldFetchRemoteModels": False,
    })


def inspect(args) -> int:
    target = _root(args.target_root)
    return _print({"type": "PortableAIInspect", "apiVersion": PORTABLE_LAYOUT_VERSION, "targetRoot": str(target), "exists": target.exists()})


def evidence_inspect(args) -> int:
    path = Path(args.path).expanduser()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _print({"path": str(path), "type": payload.get("type"), "apiVersion": payload.get("apiVersion")})
