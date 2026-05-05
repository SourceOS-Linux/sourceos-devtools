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
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


PORTABLE_LAYOUT_VERSION = "sourceos.portable-ai/v1alpha1"
BENCHMARK_SIZE_MB = 8

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

LARGE_FILE_SAFE_FSTYPES = {
    "apfs",
    "btrfs",
    "exfat",
    "ext2",
    "ext3",
    "ext4",
    "f2fs",
    "hfs",
    "hfs+",
    "ntfs",
    "ufs",
    "xfs",
    "zfs",
}

LARGE_FILE_BLOCKING_FSTYPES = {
    "fat",
    "fat16",
    "fat32",
    "msdos",
    "vfat",
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _target(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _probe_path(path: Path) -> Path:
    return path if path.exists() else path.parent


def _run(args: list[str], timeout: int = 3) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def _disk_usage_gb(path: Path) -> dict[str, float | None]:
    probe = _probe_path(path)
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
    probe = _probe_path(path)
    return probe.exists() and os.access(probe, os.W_OK)


def _host_facts() -> dict[str, Any]:
    ram_gb: float | None = None
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            ram_gb = round((pages * page_size) / (1024 ** 3), 2)
    except Exception:
        ram_gb = None

    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "cpuCount": os.cpu_count(),
        "ramGb": ram_gb,
    }


def _linux_block_details(source: str | None) -> dict[str, Any]:
    details: dict[str, Any] = {
        "baseDevice": None,
        "transport": None,
        "removableFlag": None,
        "model": None,
        "vendor": None,
    }
    if not source or not source.startswith("/dev/"):
        return details

    pk = _run(["lsblk", "-ndo", "PKNAME", source])
    base_name = pk.stdout.strip().splitlines()[0] if pk and pk.stdout.strip() else Path(source).name
    base = f"/dev/{base_name}" if not base_name.startswith("/dev/") else base_name
    details["baseDevice"] = base

    for key, column in [
        ("transport", "TRAN"),
        ("removableFlag", "RM"),
        ("model", "MODEL"),
        ("vendor", "VENDOR"),
    ]:
        result = _run(["lsblk", "-ndo", column, base])
        value = result.stdout.strip().splitlines()[0] if result and result.stdout.strip() else None
        details[key] = value
    return details


def _darwin_block_details(source: str | None) -> dict[str, Any]:
    details: dict[str, Any] = {
        "baseDevice": source,
        "transport": None,
        "removableFlag": None,
        "model": None,
        "vendor": None,
    }
    if not source or not source.startswith("/dev/"):
        return details

    result = _run(["diskutil", "info", source])
    if not result or result.returncode != 0:
        return details
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("Protocol:"):
            details["transport"] = line.split(":", 1)[1].strip()
        elif line.startswith("Removable Media:"):
            details["removableFlag"] = line.split(":", 1)[1].strip()
        elif line.startswith("Device / Media Name:"):
            details["model"] = line.split(":", 1)[1].strip()
    return details


def _mount_info(path: Path) -> dict[str, Any]:
    probe = _probe_path(path)
    info: dict[str, Any] = {
        "probePath": str(probe),
        "source": None,
        "fsType": None,
        "options": None,
        "readOnly": None,
        "largeFileSupport": "unknown",
        "largeFileReason": "filesystem type unavailable",
        "removableConfidence": "unknown",
        "block": {},
    }

    system = platform.system()
    if system == "Linux" and shutil.which("findmnt"):
        result = _run(["findmnt", "-n", "-T", str(probe), "-o", "SOURCE,FSTYPE,OPTIONS"])
        if result and result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(maxsplit=2)
            if len(parts) >= 1:
                info["source"] = parts[0]
            if len(parts) >= 2:
                info["fsType"] = parts[1].lower()
            if len(parts) >= 3:
                info["options"] = parts[2]
    elif system == "Darwin":
        df = _run(["df", "-P", str(probe)])
        if df and df.returncode == 0:
            lines = [line for line in df.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                info["source"] = lines[1].split()[0]
        mount = _run(["mount"])
        if mount and mount.returncode == 0 and info.get("source"):
            for line in mount.stdout.splitlines():
                if line.startswith(str(info["source"]) + " on "):
                    if "(" in line and ")" in line:
                        opts = line.rsplit("(", 1)[1].rstrip(")")
                        bits = [bit.strip() for bit in opts.split(",")]
                        info["fsType"] = bits[0].lower() if bits else None
                        info["options"] = ",".join(bits[1:]) if len(bits) > 1 else None
                    break

    opts = str(info.get("options") or "")
    if opts:
        info["readOnly"] = "ro" in {part.strip().lower() for part in opts.split(",")}

    fs_type = str(info.get("fsType") or "").lower()
    if fs_type in LARGE_FILE_BLOCKING_FSTYPES:
        info["largeFileSupport"] = "blocked"
        info["largeFileReason"] = f"{fs_type} has a practical 4GB per-file limit"
    elif fs_type in LARGE_FILE_SAFE_FSTYPES:
        info["largeFileSupport"] = "ok"
        info["largeFileReason"] = f"{fs_type} supports large model files"

    if system == "Linux":
        block = _linux_block_details(info.get("source"))
    elif system == "Darwin":
        block = _darwin_block_details(info.get("source"))
    else:
        block = {}
    info["block"] = block

    transport = str(block.get("transport") or "").lower()
    removable = str(block.get("removableFlag") or "").lower()
    if transport == "usb" or removable in {"1", "yes", "removable"}:
        info["removableConfidence"] = "high"
    elif info.get("source"):
        info["removableConfidence"] = "low"
    return info


def _runtime_paths() -> dict[str, str | None]:
    return {
        "ollama": shutil.which("ollama"),
        "llama-cpp": shutil.which("llama-server") or shutil.which("llama.cpp"),
        "python3": shutil.which("python3"),
    }


def _benchmark(path: Path, size_mb: int = BENCHMARK_SIZE_MB) -> dict[str, Any]:
    probe = _probe_path(path)
    result: dict[str, Any] = {
        "requested": True,
        "performed": False,
        "sizeMb": size_mb,
        "writeMBps": None,
        "readMBps": None,
        "tempFileRemoved": False,
        "error": None,
    }
    if not probe.exists() or not os.access(probe, os.W_OK):
        result["error"] = "benchmark target is not writable"
        return result

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".sourceos_portable_ai_bench_", suffix=".tmp", dir=str(probe), delete=False) as handle:
            tmp_path = handle.name
            chunk = b"0" * (1024 * 1024)
            start = time.perf_counter()
            for _ in range(size_mb):
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
            elapsed = max(time.perf_counter() - start, 1e-9)
            result["writeMBps"] = round(size_mb / elapsed, 2)

        start = time.perf_counter()
        with open(tmp_path, "rb") as handle:
            while handle.read(1024 * 1024):
                pass
        elapsed = max(time.perf_counter() - start, 1e-9)
        result["readMBps"] = round(size_mb / elapsed, 2)
        result["performed"] = True
    except Exception as exc:  # pragma: no cover - defensive around host IO
        result["error"] = str(exc)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
                result["tempFileRemoved"] = True
            except OSError:
                result["tempFileRemoved"] = False
    return result


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
    mount = _mount_info(target)
    host = _host_facts()
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
    if mount.get("readOnly") is True:
        failures.append("target mount is read-only")
    if mount.get("largeFileSupport") == "blocked":
        failures.append(str(mount.get("largeFileReason")))
    elif mount.get("largeFileSupport") == "unknown":
        warnings.append("large-file support could not be confirmed")
    if mount.get("removableConfidence") == "low":
        warnings.append("target does not appear to be removable USB media; proceed only if this is an approved portable SSD/root")

    if free_gb is not None and free_gb < 8:
        failures.append("less than 8GB free; no built-in portable profile can be prepared safely")
    elif free_gb is not None and free_gb < 16:
        warnings.append("less than 16GB free; only tiny-router or small BYOM profiles are realistic")

    ram_gb = host.get("ramGb")
    if isinstance(ram_gb, (int, float)):
        if ram_gb < 8:
            warnings.append("host RAM is below 8GB; only very small local models are realistic")
        elif ram_gb < 16:
            warnings.append("host RAM is below 16GB; prefer tiny-router or laptop-safe profiles")
    else:
        warnings.append("host RAM could not be detected")

    benchmark = {
        "requested": bool(getattr(args, "benchmark", False)),
        "performed": False,
    }
    if getattr(args, "benchmark", False):
        benchmark = _benchmark(target)
        if benchmark.get("error"):
            warnings.append(f"benchmark did not complete: {benchmark['error']}")
        elif benchmark.get("performed"):
            write_speed = benchmark.get("writeMBps") or 0
            read_speed = benchmark.get("readMBps") or 0
            if write_speed < 10:
                failures.append(f"write benchmark below minimum: {write_speed} MB/s")
            elif write_speed < 25:
                warnings.append(f"write benchmark is usable but slow: {write_speed} MB/s")
            if read_speed < 20:
                failures.append(f"read benchmark below minimum: {read_speed} MB/s")
            elif read_speed < 50:
                warnings.append(f"read benchmark is usable but slow: {read_speed} MB/s")

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
            "mount": mount,
            "host": host,
            "runtimePaths": runtime_paths,
            "benchmark": benchmark,
            "benchmarkRequested": benchmark.get("requested", False),
            "benchmarkPerformed": benchmark.get("performed", False),
            "largeFileSupportWarning": None if mount.get("largeFileSupport") == "ok" else mount.get("largeFileReason"),
            "failures": failures,
            "warnings": warnings,
            "decision": decision,
            "mutatesTarget": bool(getattr(args, "benchmark", False)),
            "mutationScope": "temporary benchmark file only" if getattr(args, "benchmark", False) else None,
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
