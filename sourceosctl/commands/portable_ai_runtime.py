from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PROVIDER = "ollama-compatible"
SUPPORTED_PROVIDERS = ["ollama-compatible", "llama.cpp", "openai-compatible-local"]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11434


def _print(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def start_plan(args) -> int:
    root = Path(args.target_root).expanduser().resolve()
    payload = {
        "type": "PortableAIStartPlan",
        "targetRoot": str(root),
        "provider": args.provider,
        "host": args.host,
        "port": args.port,
        "surface": args.surface,
        "model": args.model,
        "endpoint": f"http://{args.host}:{args.port}",
        "wouldStartProvider": False,
        "requiresAgentMachineActivation": True,
        "requiresPolicyAdmission": True,
        "promptEgressDefault": "deny",
        "toolUseDefault": "deny",
    }
    return _print(payload)


def stop_plan(args) -> int:
    root = Path(args.target_root).expanduser().resolve()
    payload = {
        "type": "PortableAIStopPlan",
        "targetRoot": str(root),
        "provider": args.provider,
        "host": args.host,
        "port": args.port,
        "endpoint": f"http://{args.host}:{args.port}",
        "wouldStopProvider": False,
        "requiresAgentMachineTeardown": True,
        "requiresPolicyAdmission": True,
    }
    return _print(payload)
