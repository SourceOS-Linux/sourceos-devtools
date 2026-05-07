"""Portable AI Kit runtime start/stop planning.

This module renders concrete runtime and surface handoff plans without starting
or stopping any process. Runtime activation remains Agent Machine gated.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
from pathlib import Path
from typing import Any, Dict

from sourceosctl.commands import portable_ai


DEFAULT_PROVIDER = "ollama-compatible"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11434
SUPPORTED_PROVIDERS = ["ollama-compatible", "llama.cpp", "openai-compatible-local"]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _target(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_portable_root(target_root: Path) -> dict[str, Any] | None:
    candidates = [
        target_root / "manifests" / "portable-ai-root.json",
        target_root / "manifests" / "portable-ai-root.laptop-safe.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            payload = _read_json(candidate)
            if payload:
                return payload
    return None


def _load_model_packs(target_root: Path) -> list[dict[str, Any]]:
    manifest_dir = target_root / "manifests"
    if not manifest_dir.exists():
        return []
    packs: list[dict[str, Any]] = []
    for path in sorted(manifest_dir.glob("model-carry-pack*.json")):
        payload = _read_json(path)
        if payload and payload.get("kind") == "ModelCarryPack":
            payload["_manifestPath"] = str(path)
            packs.append(payload)
    return packs


def _select_model_pack(model_packs: list[dict[str, Any]], requested: str | None) -> dict[str, Any] | None:
    if not model_packs:
        return None
    if requested:
        for pack in model_packs:
            model = pack.get("model", {})
            if requested in {pack.get("packId"), pack.get("displayName"), model.get("name")}:
                return pack
    return model_packs[0]


def _endpoint(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _runtime_env(target_root: Path, provider: str, host: str, port: int) -> dict[str, str]:
    if provider == "ollama-compatible":
        return {
            "OLLAMA_HOST": f"{host}:{port}",
            "OLLAMA_MODELS": str(target_root / "models" / "ollama"),
            "SOURCEOS_PORTABLE_AI_ROOT": str(target_root),
        }
    if provider == "llama.cpp":
        return {
            "LLAMA_ARG_HOST": host,
            "LLAMA_ARG_PORT": str(port),
            "SOURCEOS_PORTABLE_AI_ROOT": str(target_root),
        }
    return {
        "OPENAI_BASE_URL": _endpoint(host, port),
        "SOURCEOS_PORTABLE_AI_ROOT": str(target_root),
    }


def _runtime_command(provider: str, host: str, port: int, model_pack: dict[str, Any] | None) -> list[str]:
    if provider == "ollama-compatible":
        return ["ollama", "serve"]
    if provider == "llama.cpp":
        model_name = (model_pack or {}).get("model", {}).get("name", "<model.gguf>")
        return ["llama-server", "--host", host, "--port", str(port), "--model", model_name]
    return ["<openai-compatible-local-server>", "--host", host, "--port", str(port)]


def _surface_handoff(surface: str, endpoint: str, provider: str) -> dict[str, Any]:
    return {
        "surface": surface,
        "endpoint": endpoint,
        "provider": provider,
        "handoffKind": "local-endpoint-ref",
        "secretFree": True,
        "promptEgressDefault": "deny",
        "toolUseDefault": "deny",
    }


def start_plan(args) -> int:
    """Render a concrete runtime/surface launch plan without starting daemons."""
    target_root = _target(args.target_root)
    provider = args.provider
    host = args.host
    port = args.port
    model_packs = _load_model_packs(target_root)
    selected_pack = _select_model_pack(model_packs, args.model)
    endpoint = _endpoint(host, port)
    env = _runtime_env(target_root, provider, host, port)
    command = _runtime_command(provider, host, port, selected_pack)
    runtime_binary = shutil.which(command[0]) if command and not command[0].startswith("<") else None

    warnings: list[str] = []
    if provider == "ollama-compatible" and runtime_binary is None:
        warnings.append("ollama binary was not found on PATH; install/stage runtime before activation")
    if provider == "llama.cpp" and runtime_binary is None:
        warnings.append("llama-server binary was not found on PATH; install/stage runtime before activation")
    if not selected_pack:
        warnings.append("no ModelCarryPack manifest found; runtime can be staged but model route is not selected")

    return _print_json(
        {
            "type": "PortableAIStartPlan",
            "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
            "capturedAt": _now(),
            "targetRoot": str(target_root),
            "portableRootManifestPresent": _load_portable_root(target_root) is not None,
            "provider": provider,
            "surface": args.surface,
            "endpoint": endpoint,
            "bindAddress": host,
            "port": port,
            "runtimeBinary": runtime_binary,
            "runtimeEnv": env,
            "runtimeCommand": command,
            "modelPacksFound": len(model_packs),
            "selectedModelPack": selected_pack,
            "surfaceHandoff": _surface_handoff(args.surface, endpoint, provider),
            "wouldStartRuntime": False,
            "wouldContactProvider": False,
            "wouldDownloadModel": False,
            "requiresAgentMachineActivation": True,
            "requiresPolicyAdmission": True,
            "requiresAgentRegistryGrant": True,
            "promptEgressDefault": "deny",
            "hostWritesDefault": "deny",
            "networkDefault": "loopback-only",
            "stopPlanCommand": [
                "python3",
                "bin/sourceosctl",
                "portable-ai",
                "stop-plan",
                str(target_root),
                "--provider",
                provider,
                "--host",
                host,
                "--port",
                str(port),
            ],
            "warnings": warnings,
        }
    )


def stop_plan(args) -> int:
    """Render a concrete runtime teardown plan without killing processes."""
    target_root = _target(args.target_root)
    provider = args.provider
    host = args.host
    port = args.port
    endpoint = _endpoint(host, port)

    if provider == "ollama-compatible":
        processMatch = "ollama serve"
    elif provider == "llama.cpp":
        processMatch = "llama-server"
    else:
        processMatch = "openai-compatible-local-server"

    return _print_json(
        {
            "type": "PortableAIStopPlan",
            "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
            "capturedAt": _now(),
            "targetRoot": str(target_root),
            "provider": provider,
            "endpoint": endpoint,
            "bindAddress": host,
            "port": port,
            "processMatchHint": processMatch,
            "wouldStopRuntime": False,
            "wouldKillProcesses": False,
            "requiresOperatorConfirmation": True,
            "requiresAgentMachineTeardown": True,
            "teardownEvidenceExpected": True,
            "safeEjectRequires": [
                "runtime process stopped",
                "loopback port released",
                "temporary runtime files flushed",
                "PortableRuntimeTeardownReceipt written",
            ],
            "operatorGuidance": [
                "Use Agent Machine teardown once activation support lands.",
                "Until then, stop only the runtime process that matches the endpoint/provider in this plan.",
                "Do not remove model blobs or evidence unless running an explicit wipe flow.",
            ],
        }
    )
