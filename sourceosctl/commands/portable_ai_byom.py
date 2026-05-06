"""Portable AI Kit BYOM model verification helpers.

This module handles local bring-your-own model file verification. It never
contacts a network endpoint and never downloads model weights.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

from sourceosctl.commands import portable_ai


DEFAULT_TASK_CLASSES = ["operator-selected"]
CHUNK_SIZE = 1024 * 1024


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-._")
    return slug or "operator-supplied-model"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _target(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _model_path(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def _manifest_path(target_root: Path, slug: str) -> Path:
    return target_root / "manifests" / f"model-carry-pack.byom-gguf.{slug}.json"


def _copied_model_path(target_root: Path, source: Path) -> Path:
    return target_root / "models" / "blobs" / source.name


def _build_pack(
    *,
    pack_id: str,
    display_name: str,
    model_file: Path,
    sha256: str,
    size_bytes: int,
    license_ref: str,
    source_note: str | None,
    task_classes: list[str],
    copied_to: Path | None,
) -> dict[str, Any]:
    size_mb = max(1, round(size_bytes / (1024 * 1024)))
    return {
        "schemaVersion": "v0.1",
        "kind": "ModelCarryPack",
        "packId": pack_id,
        "displayName": display_name,
        "profileKey": "byom-gguf",
        "model": {
            "name": model_file.name,
            "family": "operator-supplied",
            "parameterClass": "other",
            "quantization": "operator-supplied",
            "format": "gguf",
            "contextWindowHint": None,
            "diskSizeHintMb": size_mb,
            "memoryHintMb": None,
        },
        "runtimeCompatibility": ["llama.cpp", "ollama-compatible", "openai-compatible-local"],
        "footprint": {
            "minimumFreeGb": 8,
            "recommendedFreeGb": 64,
            "minimumRamGb": 8,
            "recommendedRamGb": 32,
        },
        "provenance": {
            "sourceKind": "local-file",
            "sourceUrl": None,
            "sourceNote": source_note,
            "licenseRef": license_ref,
            "modelCardRef": None,
            "sha256": sha256,
            "sha256RequiredBeforeEligibility": True,
        },
        "taskClasses": task_classes,
        "labels": ["local-only", "byom-verified"],
        "policy": {
            "localOnlyDefault": True,
            "promptEgressDefault": "deny",
            "allowToolUseDefault": False,
            "allowNetworkDefault": False,
            "requiresExplicitImport": True,
            "requiresEvidence": True,
            "eligibleForRoutingBeforeHash": False,
            "maxPromptChars": None,
        },
        "storage": {
            "sourcePath": str(model_file),
            "copiedToPortableRoot": str(copied_to) if copied_to else None,
        },
        "evidence": {
            "emitPackVerification": True,
            "emitRuntimeHealth": True,
            "emitRouteDecision": True,
            "emitPromptHashOnly": True,
        },
        "notes": "Operator-supplied local model file verified by SourceOS Portable AI Kit. No download was performed.",
    }


def verify(args) -> int:
    """Verify a local BYOM model file and optionally write a carry-pack manifest."""
    target_root = _target(args.target_root)
    model_file = _model_path(args.model_file)
    failures: list[str] = []
    warnings: list[str] = []

    if not model_file.exists():
        failures.append("model file does not exist")
    elif not model_file.is_file():
        failures.append("model path is not a regular file")

    if model_file.suffix.lower() != ".gguf":
        warnings.append("model file does not end with .gguf; treat this as an operator-attested local model only")

    if getattr(args, "execute", False) and not getattr(args, "policy_ok", False):
        failures.append("--execute requires --policy-ok")

    target_manifest_dir = target_root / "manifests"
    target_blob_dir = target_root / "models" / "blobs"
    if getattr(args, "execute", False):
        if not target_root.exists():
            failures.append("target root does not exist; run portable-ai prepare first")
        if target_root.exists() and not target_manifest_dir.exists():
            failures.append("target root is missing manifests directory; run portable-ai prepare first")
        if getattr(args, "copy", False) and target_root.exists() and not target_blob_dir.exists():
            failures.append("target root is missing models/blobs directory; run portable-ai prepare first")

    if failures:
        return _print_json(
            {
                "type": "BYOMImportEvidence",
                "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
                "capturedAt": _now(),
                "targetRoot": str(target_root),
                "modelFile": str(model_file),
                "decision": "fail",
                "failures": failures,
                "warnings": warnings,
                "wouldWriteManifest": False,
                "wouldCopyModel": False,
                "downloadedModel": False,
            }
        )

    size_bytes = model_file.stat().st_size
    sha256 = _sha256_file(model_file)
    slug = _safe_slug(args.name or model_file.stem)
    pack_id = args.pack_id or f"urn:srcos:model-carry-pack:byom-gguf-{slug}"
    display_name = args.display_name or args.name or model_file.stem
    task_classes = args.task_class or DEFAULT_TASK_CLASSES
    copied_to = _copied_model_path(target_root, model_file) if getattr(args, "copy", False) else None
    manifest = _build_pack(
        pack_id=pack_id,
        display_name=display_name,
        model_file=model_file,
        sha256=sha256,
        size_bytes=size_bytes,
        license_ref=args.license_ref,
        source_note=args.source_note,
        task_classes=task_classes,
        copied_to=copied_to,
    )
    manifest_path = _manifest_path(target_root, slug)

    if not getattr(args, "execute", False):
        return _print_json(
            {
                "type": "BYOMImportPlan",
                "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
                "capturedAt": _now(),
                "targetRoot": str(target_root),
                "modelFile": str(model_file),
                "sizeBytes": size_bytes,
                "sha256": sha256,
                "licenseRef": args.license_ref,
                "packId": pack_id,
                "manifestPath": str(manifest_path),
                "wouldWriteManifest": True,
                "wouldCopyModel": bool(getattr(args, "copy", False)),
                "copyDestination": str(copied_to) if copied_to else None,
                "downloadedModel": False,
                "requiresExecuteAndPolicyOk": True,
                "manifest": manifest,
                "warnings": warnings,
            }
        )

    target_manifest_dir.mkdir(parents=True, exist_ok=True)
    copied = False
    if getattr(args, "copy", False):
        target_blob_dir.mkdir(parents=True, exist_ok=True)
        assert copied_to is not None
        shutil.copy2(model_file, copied_to)
        copied = True

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence = {
        "type": "BYOMImportEvidence",
        "apiVersion": portable_ai.PORTABLE_LAYOUT_VERSION,
        "capturedAt": _now(),
        "targetRoot": str(target_root),
        "modelFile": str(model_file),
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "licenseRef": args.license_ref,
        "sourceNote": args.source_note,
        "packId": pack_id,
        "manifestPath": str(manifest_path),
        "manifestWritten": True,
        "modelCopied": copied,
        "copyDestination": str(copied_to) if copied_to else None,
        "downloadedModel": False,
        "promptEgressDefault": "deny",
        "toolUseDefault": "deny",
        "networkDefault": "deny",
        "decision": "verified",
        "warnings": warnings,
    }
    if getattr(args, "evidence_out", None):
        Path(args.evidence_out).expanduser().write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return _print_json(evidence)
