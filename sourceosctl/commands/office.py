"""office command helpers.

This module implements the first read-only / dry-run slice of the SourceOS
Office Plane.  It does not create, convert, or modify files.  It renders
structured plans that can later be executed under policy by LibreOffice,
Collabora, ONLYOFFICE, Microsoft Graph, Google Workspace, or SourceOS-native
backends.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_WORKROOM_ID = "workroom-local-default"
DEFAULT_OUTPUT_ROOT = "~/Documents/SourceOS/agent-output"
DEFAULT_DOWNLOADS_ROOT = "~/Downloads/SourceOS/agent-downloads"
DEFAULT_TEMPLATE_ROOT = "~/dev"

OFFICE_ARTIFACT_SCHEMA = "https://socioprophet.io/schemas/workspace/office-artifact.schema.json"
PROFESSIONAL_WORKROOM_SCHEMA = "https://socioprophet.io/schemas/workspace/professional-workroom.schema.json"

SUPPORTED_ARTIFACT_TYPES = [
    "document",
    "spreadsheet",
    "slide-deck",
    "pdf",
    "mail-draft",
    "calendar-item",
    "task-list",
    "note",
    "media-asset",
]

SUPPORTED_FORMATS = [
    "docx",
    "odt",
    "md",
    "pdf",
    "xlsx",
    "ods",
    "csv",
    "pptx",
    "odp",
    "eml",
    "ics",
    "json",
    "txt",
    "png",
    "jpg",
    "wav",
    "m4a",
]

DEFAULT_BACKEND_BY_MODE = {
    "local-headless": "libreoffice",
    "browser-collab": "collabora",
    "remote-api": "microsoft-graph",
    "native": "sourceos-native",
    "manual-upload": "manual",
}


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _redact_home(path: str) -> str:
    home = str(Path.home())
    expanded = _expand(path)
    if expanded == home:
        return "$HOME"
    if expanded.startswith(home + os.sep):
        return "$HOME" + expanded[len(home) :]
    return expanded


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _which_any(candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _libreoffice_path() -> Optional[str]:
    # Homebrew/macOS may expose `soffice` or `libreoffice`; Linux distributions vary.
    return _which_any(["soffice", "libreoffice", "lowriter"])


def _sha256(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _artifact_plan(args, operation: str) -> Dict[str, Any]:
    artifact_type = getattr(args, "artifact_type", None) or "document"
    fmt = getattr(args, "format", None) or "docx"
    title = getattr(args, "title", None) or "Untitled Office Artifact"
    workroom_id = getattr(args, "workroom_id", None) or DEFAULT_WORKROOM_ID
    output_root = getattr(args, "output_root", None) or DEFAULT_OUTPUT_ROOT
    backend = getattr(args, "backend", None) or "libreoffice"
    mode = getattr(args, "mode", None) or "local-headless"

    slug = title.lower().strip().replace(" ", "-") or "office-artifact"
    safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_")[:80] or "office-artifact"
    storage_ref = f"sourceos-office://{workroom_id}/output/{safe_slug}.{fmt}"

    return {
        "type": "OfficeArtifactPlan",
        "specVersion": "0.1.0",
        "operation": operation,
        "dryRun": True,
        "contracts": {
            "officeArtifactSchema": OFFICE_ARTIFACT_SCHEMA,
            "professionalWorkroomSchema": PROFESSIONAL_WORKROOM_SCHEMA,
        },
        "officeArtifact": {
            "schemaVersion": "v0.1",
            "artifactId": f"office-artifact-{safe_slug}",
            "workroomId": workroom_id,
            "artifactType": artifact_type,
            "title": title,
            "status": "draft",
            "format": fmt,
            "storageRef": storage_ref,
            "backend": {
                "engine": backend,
                "mode": mode,
                "versionRef": f"urn:srcos:office-backend:{backend}-{mode}",
            },
            "agentRunRefs": [],
            "policyRefs": [],
            "evidenceRefs": [],
            "labels": {
                "sourceos.surface": "office-plane",
                "sourceos.operation": operation,
            },
        },
        "paths": {
            "outputRoot": _redact_home(output_root),
            "downloadsRoot": _redact_home(getattr(args, "downloads_root", DEFAULT_DOWNLOADS_ROOT)),
            "templateRoot": _redact_home(getattr(args, "template_root", DEFAULT_TEMPLATE_ROOT)),
        },
        "sideEffectPolicy": {
            "createsFiles": operation in {"generate", "convert"},
            "currentlyExecuted": False,
            "requiresHumanReviewBeforeExternalSend": True,
            "mailSendDeniedByDefault": True,
        },
    }


def doctor(args) -> int:
    """Inspect local Office Plane dependencies without mutating state."""
    lo = _libreoffice_path()
    payload = {
        "type": "OfficeDoctor",
        "specVersion": "0.1.0",
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "backends": {
            "libreoffice": {
                "available": lo is not None,
                "path": lo,
                "mode": "local-headless",
                "role": "default SourceOS local render/generate/convert backend",
            },
            "collabora": {
                "available": False,
                "mode": "browser-collab",
                "role": "future WOPI/browser collaboration backend",
            },
            "onlyoffice": {
                "available": False,
                "mode": "browser-collab or document-builder",
                "role": "future optional DOCX/XLSX/PPTX builder/editor backend",
            },
        },
        "contracts": {
            "officeArtifactSchema": OFFICE_ARTIFACT_SCHEMA,
            "professionalWorkroomSchema": PROFESSIONAL_WORKROOM_SCHEMA,
        },
    }
    return _print_json(payload)


def plan(args) -> int:
    """Render an OfficeArtifact-compatible plan."""
    return _print_json(_artifact_plan(args, "plan"))


def generate(args) -> int:
    """Render a generation plan.  Dry-run only."""
    if not getattr(args, "dry_run", True):
        print("error: office generate is dry-run only in this release", file=sys.stderr)
        return 1
    payload = _artifact_plan(args, "generate")
    payload["templateRef"] = getattr(args, "template", None)
    payload["generationInputs"] = {
        "promptRef": getattr(args, "prompt_ref", None),
        "dataRef": getattr(args, "data_ref", None),
    }
    return _print_json(payload)


def convert(args) -> int:
    """Render a conversion plan.  Dry-run only."""
    if not getattr(args, "dry_run", True):
        print("error: office convert is dry-run only in this release", file=sys.stderr)
        return 1
    payload = _artifact_plan(args, "convert")
    payload["conversion"] = {
        "input": _redact_home(args.input),
        "inputExists": Path(_expand(args.input)).exists(),
        "toFormat": args.to,
        "outputRoot": _redact_home(getattr(args, "output_root", DEFAULT_OUTPUT_ROOT)),
        "backendCommand": "soffice --headless --convert-to <format> --outdir <outputRoot> <input>",
        "willExecute": False,
    }
    return _print_json(payload)


def inspect(args) -> int:
    """Inspect an Office artifact file without modifying it."""
    path = Path(_expand(args.path))
    if not path.exists():
        print(f"error: office artifact not found: {args.path}", file=sys.stderr)
        return 1
    if not path.is_file():
        print(f"error: office artifact is not a file: {args.path}", file=sys.stderr)
        return 1

    suffix = path.suffix.lower().lstrip(".")
    mime_type, _ = mimetypes.guess_type(str(path))
    payload = {
        "type": "OfficeArtifactInspection",
        "specVersion": "0.1.0",
        "path": _redact_home(str(path)),
        "exists": True,
        "sizeBytes": path.stat().st_size,
        "format": suffix or None,
        "supportedFormat": suffix in SUPPORTED_FORMATS,
        "mimeType": mime_type,
        "sha256": _sha256(path),
        "contracts": {
            "officeArtifactSchema": OFFICE_ARTIFACT_SCHEMA,
        },
    }
    return _print_json(payload)


def evidence_inspect(args) -> int:
    """Inspect an Office Plane evidence JSON file."""
    path = Path(args.path)
    if not path.exists():
        print(f"error: evidence file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    office_artifact = payload.get("officeArtifact", {}) if isinstance(payload, dict) else {}
    summary = {
        "path": str(path),
        "type": payload.get("type") if isinstance(payload, dict) else None,
        "artifactId": office_artifact.get("artifactId") if isinstance(office_artifact, dict) else payload.get("artifactId"),
        "workroomId": office_artifact.get("workroomId") if isinstance(office_artifact, dict) else payload.get("workroomId"),
        "artifactType": office_artifact.get("artifactType") if isinstance(office_artifact, dict) else payload.get("artifactType"),
        "format": office_artifact.get("format") if isinstance(office_artifact, dict) else payload.get("format"),
        "evidenceRefs": office_artifact.get("evidenceRefs", []) if isinstance(office_artifact, dict) else payload.get("evidenceRefs", []),
    }
    return _print_json(summary)
