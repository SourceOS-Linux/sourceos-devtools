"""Local Model Door helpers.

This module probes local model runtime state and renders routing/profile plans.
It never pulls weights, starts daemons, sends prompts, or performs inference.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


DEFAULT_PROFILE_REF = "urn:srcos:model-profile:local-llama32-1b"
QUALITY_PROFILE_REF = "urn:srcos:model-profile:local-llama32-3b"
DEFAULT_ROUTER_BINDING_REF = "urn:socioprophet:model-router-binding:demo-user-local-llama32"

LOCAL_MODEL_PROFILES = {
    "local-llama32-1b": {
        "profileRef": DEFAULT_PROFILE_REF,
        "displayName": "Local Llama 3.2 1B Router",
        "runtime": "ollama",
        "model": "llama3.2:1b",
        "parameterClass": "1b",
        "roles": [
            "router",
            "triage",
            "summarization",
            "rewrite",
            "office-assist",
            "agent-machine-assist",
            "offline-fallback",
            "privacy-first-chat",
        ],
        "policy": {
            "localOnlyDefault": True,
            "sendPromptOffDeviceDefault": False,
            "allowToolUse": False,
            "allowNetwork": False,
            "requiresExplicitPull": True,
        },
    },
    "local-llama32-3b": {
        "profileRef": QUALITY_PROFILE_REF,
        "displayName": "Local Llama 3.2 3B Quality Fallback",
        "runtime": "ollama",
        "model": "llama3.2:3b",
        "parameterClass": "3b",
        "roles": [
            "summarization",
            "rewrite",
            "office-assist",
            "agent-machine-assist",
            "offline-fallback",
            "coding-assist",
            "privacy-first-chat",
        ],
        "policy": {
            "localOnlyDefault": True,
            "sendPromptOffDeviceDefault": False,
            "allowToolUse": False,
            "allowNetwork": False,
            "requiresExplicitPull": True,
        },
    },
}


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _ollama_path() -> str | None:
    return shutil.which("ollama")


def _ollama_list() -> dict[str, Any]:
    path = _ollama_path()
    if not path:
        return {"available": False, "path": None, "models": [], "error": "ollama not found on PATH"}
    try:
        completed = subprocess.run(
            [path, "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:  # pragma: no cover - defensive around host runtime
        return {"available": True, "path": path, "models": [], "error": str(exc)}

    models: list[str] = []
    for line in completed.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return {
        "available": True,
        "path": path,
        "returnCode": completed.returncode,
        "models": models,
        "error": completed.stderr.strip() or None,
    }


def _profile(profile_name: str) -> dict[str, Any]:
    try:
        return LOCAL_MODEL_PROFILES[profile_name]
    except KeyError:
        known = ", ".join(sorted(LOCAL_MODEL_PROFILES))
        raise SystemExit(f"unknown local model profile: {profile_name}; known profiles: {known}")


def _prompt_hash(text: str | None) -> str | None:
    if text is None:
        return None
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def doctor(args) -> int:
    """Inspect local model runtime availability without pulling or running models."""
    runtime = _ollama_list()
    installed = set(runtime.get("models", []))
    profiles = []
    for profile in LOCAL_MODEL_PROFILES.values():
        model = profile["model"]
        profiles.append(
            {
                "profileRef": profile["profileRef"],
                "model": model,
                "runtime": profile["runtime"],
                "installed": model in installed,
                "roles": profile["roles"],
            }
        )
    return _print_json(
        {
            "type": "LocalModelDoctor",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "runtime": runtime,
            "profiles": profiles,
            "policy": {
                "pullsModels": False,
                "startsServices": False,
                "runsInference": False,
                "promptEgressDefault": "deny",
                "promptEvidence": "hash-only",
            },
        }
    )


def profiles(args) -> int:
    """List built-in local model profile refs consumed from sourceos-model-carry."""
    return _print_json(
        {
            "type": "LocalModelProfiles",
            "profiles": LOCAL_MODEL_PROFILES,
            "sourceRepo": "SourceOS-Linux/sourceos-model-carry",
        }
    )


def plan(args) -> int:
    """Render a local model runtime plan without pulling or running models."""
    profile = _profile(args.profile)
    runtime = _ollama_list()
    installed = profile["model"] in set(runtime.get("models", []))
    return _print_json(
        {
            "type": "LocalModelPlan",
            "profile": profile,
            "runtime": runtime,
            "installed": installed,
            "wouldPull": False,
            "wouldStartService": False,
            "wouldRunInference": False,
            "explicitInstallCommand": f"ollama pull {profile['model']}",
            "explicitRunCommand": f"ollama run {profile['model']}",
            "policy": profile["policy"],
        }
    )


def route(args) -> int:
    """Render a hash-only route decision for a task class."""
    runtime = _ollama_list()
    installed = set(runtime.get("models", []))
    default = LOCAL_MODEL_PROFILES["local-llama32-1b"]
    quality = LOCAL_MODEL_PROFILES["local-llama32-3b"]
    has_default = default["model"] in installed
    has_quality = quality["model"] in installed

    target = "base-local" if has_default else "quality-local" if has_quality else "hosted-policy-required"
    if args.task_class in {"office-assist", "rewrite", "summarization"} and args.personalization_ref:
        target = "personal-local-policy-checked"

    return _print_json(
        {
            "type": "LocalModelRouteDecision",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "taskClass": args.task_class,
            "target": target,
            "defaultLocalProfileRef": DEFAULT_PROFILE_REF,
            "qualityFallbackLocalProfileRef": QUALITY_PROFILE_REF,
            "routerBindingRef": args.router_binding_ref,
            "personalizationRef": args.personalization_ref,
            "promptHash": _prompt_hash(args.prompt) if args.prompt else None,
            "promptStored": False,
            "runtimeAvailable": runtime.get("available", False),
            "installedModels": sorted(installed),
            "requiresPolicyForHostedFallback": target == "hosted-policy-required",
            "evidence": {
                "emitRouteDecision": True,
                "emitRuntimeHealth": True,
                "emitGovernanceRefs": True,
                "promptHashOnly": True,
            },
        }
    )


def evidence_inspect(args) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: evidence file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    return _print_json(
        {
            "path": str(path),
            "type": payload.get("type"),
            "taskClass": payload.get("taskClass"),
            "target": payload.get("target"),
            "promptStored": payload.get("promptStored"),
            "promptHashPresent": bool(payload.get("promptHash")),
            "routerBindingRef": payload.get("routerBindingRef"),
        }
    )
