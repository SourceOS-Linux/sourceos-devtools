"""office command helpers.

This module implements SourceOS Office Plane planning plus guarded local
execution and quality gates.  Dry-run remains the default.  File-writing
behavior is available only behind --execute --policy-ok, writes only to
explicit output roots, and emits OfficeArtifactEvidence-compatible JSON.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from sourceosctl.commands.ooxml import (
    OOXML_GENERATION_FORMATS,
    validate_ooxml_artifact,
    write_ooxml_artifact,
)


DEFAULT_WORKROOM_ID = "workroom-local-default"
DEFAULT_OUTPUT_ROOT = "~/Documents/SourceOS/agent-output"
DEFAULT_DOWNLOADS_ROOT = "~/Downloads/SourceOS/agent-downloads"
DEFAULT_TEMPLATE_ROOT = "~/dev"

OFFICE_ARTIFACT_SCHEMA = "https://socioprophet.io/schemas/workspace/office-artifact.schema.json"
PROFESSIONAL_WORKROOM_SCHEMA = "https://socioprophet.io/schemas/workspace/professional-workroom.schema.json"
OFFICE_EVIDENCE_SCHEMA = "https://github.com/SocioProphet/agentplane/blob/main/schemas/office-artifact-evidence.schema.v0.1.json"

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

TEXT_GENERATION_FORMATS = {"txt", "md", "json"}
GUARDED_GENERATION_FORMATS = TEXT_GENERATION_FORMATS | OOXML_GENERATION_FORMATS

DEFAULT_BACKEND_BY_MODE = {
    "local-headless": "libreoffice",
    "browser-collab": "collabora",
    "remote-api": "microsoft-graph",
    "native": "sourceos-native",
    "manual-upload": "manual",
}


def _expand(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _home() -> str:
    return str(Path.home())


def _redact_home(path: str | None) -> str | None:
    if path is None:
        return None
    home = _home()
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


def _policy_hash(payload: Dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def _safe_slug(title: str) -> str:
    slug = title.lower().strip().replace(" ", "-") or "office-artifact"
    return "".join(ch for ch in slug if ch.isalnum() or ch in "-_")[:80] or "office-artifact"


def _is_forbidden_output_root(path: str) -> Optional[str]:
    expanded = _expand(path)
    if expanded == _home():
        return "whole-home output root is forbidden"
    if expanded == _expand("~/Downloads"):
        return "whole Downloads directory is forbidden; use ~/Downloads/SourceOS/agent-downloads"
    forbidden_fragments = [
        ".ssh",
        ".gnupg",
        "Library/Keychains",
        "Library/Application Support/Google/Chrome",
        "Library/Application Support/Firefox",
        ".aws",
        ".config/gcloud",
        ".azure",
        ".kube",
        "group.com.apple.notes",
        "Photos.photoslibrary",
        "Voice Memos",
        "VoiceMemos",
        "Reminders",
    ]
    for fragment in forbidden_fragments:
        if fragment in expanded:
            return f"sensitive output path fragment denied: {fragment}"
    return None


def _artifact_plan(args, operation: str, format_override: Optional[str] = None) -> Dict[str, Any]:
    artifact_type = getattr(args, "artifact_type", None) or "document"
    fmt = format_override or getattr(args, "format", None) or "docx"
    title = getattr(args, "title", None) or "Untitled Office Artifact"
    workroom_id = getattr(args, "workroom_id", None) or DEFAULT_WORKROOM_ID
    output_root = getattr(args, "output_root", None) or DEFAULT_OUTPUT_ROOT
    backend = getattr(args, "backend", None) or "libreoffice"
    mode = getattr(args, "mode", None) or "local-headless"

    safe_slug = _safe_slug(title)
    storage_ref = f"sourceos-office://{workroom_id}/output/{safe_slug}.{fmt}"

    plan = {
        "type": "OfficeArtifactPlan",
        "specVersion": "0.1.0",
        "operation": operation,
        "dryRun": not bool(getattr(args, "execute", False)),
        "contracts": {
            "officeArtifactSchema": OFFICE_ARTIFACT_SCHEMA,
            "professionalWorkroomSchema": PROFESSIONAL_WORKROOM_SCHEMA,
            "officeArtifactEvidenceSchema": OFFICE_EVIDENCE_SCHEMA,
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
    plan["policyHash"] = _policy_hash(plan["officeArtifact"])
    return plan


def _artifact_output_path(args, fmt: str) -> Path:
    title = getattr(args, "title", None) or "Untitled Office Artifact"
    return Path(_expand(getattr(args, "output_root", DEFAULT_OUTPUT_ROOT))) / f"{_safe_slug(title)}.{fmt}"


def _artifact_type_for_format(fmt: str) -> str:
    if fmt in {"xlsx", "ods", "csv"}:
        return "spreadsheet"
    if fmt in {"pptx", "odp"}:
        return "slide-deck"
    if fmt == "pdf":
        return "pdf"
    return "document"


def _build_evidence(
    *,
    plan: Dict[str, Any],
    operation: str,
    status: str,
    output_path: Path | None,
    source_refs: list[str] | None = None,
    derived_refs: list[str] | None = None,
    conversion: Dict[str, Any] | None = None,
    notes: str = "sourceosctl guarded local Office Plane evidence",
) -> Dict[str, Any]:
    artifact = plan["officeArtifact"]
    artifact_hashes = []
    if output_path and output_path.exists() and output_path.is_file():
        mime_type, _ = mimetypes.guess_type(str(output_path))
        artifact_hashes.append(
            {
                "ref": artifact["storageRef"],
                "sha256": _sha256(output_path),
                "mimeType": mime_type,
                "sizeBytes": output_path.stat().st_size,
            }
        )
    return {
        "kind": "OfficeArtifactEvidence",
        "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "workroomId": artifact["workroomId"],
        "artifactId": artifact["artifactId"],
        "artifactType": artifact["artifactType"],
        "format": artifact["format"],
        "operation": operation,
        "status": status,
        "storageRef": artifact["storageRef"],
        "sourceRefs": source_refs or [],
        "derivedRefs": derived_refs or [],
        "agentRunRef": None,
        "mountEvidenceRef": None,
        "officeArtifactContractRef": OFFICE_ARTIFACT_SCHEMA,
        "backend": artifact["backend"],
        "artifactHashes": artifact_hashes,
        "conversion": conversion,
        "review": {
            "required": True,
            "decision": "pending",
            "decisionRef": None,
            "reviewer": None,
        },
        "sideEffects": {
            "emailSent": False,
            "externalPublished": False,
            "calendarModified": False,
            "requiresPolicyApproval": True,
        },
        "policyHash": plan["policyHash"],
        "policyRefs": [],
        "redactionSummary": {
            "hostUserRedacted": True,
            "secretLikeValuesRedacted": 0,
            "notes": notes,
        },
    }


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    target = Path(_expand(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _require_execute_policy(args, operation: str) -> Optional[str]:
    if not bool(getattr(args, "execute", False)):
        return None
    if not bool(getattr(args, "policy_ok", False)):
        return f"office {operation} --execute requires --policy-ok"
    output_root = getattr(args, "output_root", DEFAULT_OUTPUT_ROOT)
    return _is_forbidden_output_root(output_root)


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
    """Render or execute guarded text/json/OOXML generation."""
    execute = bool(getattr(args, "execute", False))
    payload = _artifact_plan(args, "generate")
    payload["templateRef"] = getattr(args, "template", None)
    payload["generationInputs"] = {
        "promptRef": getattr(args, "prompt_ref", None),
        "dataRef": getattr(args, "data_ref", None),
    }
    if not execute:
        return _print_json(payload)

    error = _require_execute_policy(args, "generate")
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    fmt = payload["officeArtifact"]["format"]
    if fmt not in GUARDED_GENERATION_FORMATS:
        print(
            "error: guarded generation currently supports txt, md, json, docx, xlsx, and pptx; use convert or backend adapters for other formats",
            file=sys.stderr,
        )
        return 1

    output_path = _artifact_output_path(args, fmt)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        notes = "sourceosctl guarded JSON Office Plane artifact generation"
    elif fmt in TEXT_GENERATION_FORMATS:
        output_path.write_text(
            f"# {payload['officeArtifact']['title']}\n\n"
            "Generated by sourceosctl Office Plane guarded execution.\n\n"
            f"Workroom: {payload['officeArtifact']['workroomId']}\n"
            f"Artifact: {payload['officeArtifact']['artifactId']}\n",
            encoding="utf-8",
        )
        notes = "sourceosctl guarded text/Markdown Office Plane artifact generation"
    else:
        write_ooxml_artifact(
            fmt=fmt,
            path=output_path,
            title=payload["officeArtifact"]["title"],
            workroom_id=payload["officeArtifact"]["workroomId"],
            artifact_id=payload["officeArtifact"]["artifactId"],
        )
        structural = validate_ooxml_artifact(output_path, fmt)
        notes = f"sourceosctl guarded minimal OOXML Office Plane artifact generation; structuralValid={structural['valid']}"

    evidence = _build_evidence(
        plan=payload,
        operation="generate",
        status="requires-review",
        output_path=output_path,
        notes=notes,
    )
    evidence_out = getattr(args, "evidence_out", None)
    if evidence_out:
        _write_json(evidence_out, evidence)

    return _print_json(
        {
            "type": "OfficeGenerateResult",
            "executed": True,
            "outputPath": _redact_home(str(output_path)),
            "evidenceOut": _redact_home(evidence_out) if evidence_out else None,
            "evidence": None if evidence_out else evidence,
        }
    )


def convert(args) -> int:
    """Render or execute a guarded LibreOffice conversion."""
    execute = bool(getattr(args, "execute", False))
    payload = _artifact_plan(args, "convert", format_override=args.to)
    input_path = Path(_expand(args.input))
    output_root = Path(_expand(getattr(args, "output_root", DEFAULT_OUTPUT_ROOT)))
    inferred_output = output_root / f"{input_path.stem}.{args.to}"
    payload["conversion"] = {
        "input": _redact_home(args.input),
        "inputExists": input_path.exists(),
        "toFormat": args.to,
        "outputRoot": _redact_home(str(output_root)),
        "backendCommand": "soffice --headless --convert-to <format> --outdir <outputRoot> <input>",
        "willExecute": execute,
    }
    if not execute:
        return _print_json(payload)

    error = _require_execute_policy(args, "convert")
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if not input_path.exists() or not input_path.is_file():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 1
    if args.to not in SUPPORTED_FORMATS:
        print(f"error: unsupported target format: {args.to}", file=sys.stderr)
        return 1
    lo = _libreoffice_path()
    if not lo:
        print("error: LibreOffice/soffice not found on PATH", file=sys.stderr)
        return 1

    output_root.mkdir(parents=True, exist_ok=True)
    cmd = [lo, "--headless", "--convert-to", args.to, "--outdir", str(output_root), str(input_path)]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180)
    status = "success" if completed.returncode == 0 and inferred_output.exists() else "failure"
    evidence = _build_evidence(
        plan=payload,
        operation="convert",
        status=status,
        output_path=inferred_output if inferred_output.exists() else None,
        source_refs=[_redact_home(str(input_path)) or str(input_path)],
        derived_refs=[payload["officeArtifact"]["storageRef"]] if inferred_output.exists() else [],
        conversion={
            "fromFormat": input_path.suffix.lower().lstrip(".") or None,
            "toFormat": args.to,
            "commandRef": "sourceosctl.office.convert.local-headless",
            "executed": True,
        },
        notes=f"stdout={completed.stdout[-200:]!r}; stderr={completed.stderr[-200:]!r}",
    )
    evidence_out = getattr(args, "evidence_out", None)
    if evidence_out:
        _write_json(evidence_out, evidence)

    result = {
        "type": "OfficeConvertResult",
        "executed": True,
        "returnCode": completed.returncode,
        "status": status,
        "outputPath": _redact_home(str(inferred_output)) if inferred_output.exists() else None,
        "evidenceOut": _redact_home(evidence_out) if evidence_out else None,
        "evidence": None if evidence_out else evidence,
    }
    return _print_json(result) if status == "success" else (_print_json(result) or 1)


def validate(args) -> int:
    """Validate an Office artifact with structural and optional round-trip gates."""
    path = Path(_expand(args.path))
    fmt = getattr(args, "format", None) or path.suffix.lower().lstrip(".")
    structural = validate_ooxml_artifact(path, fmt) if fmt in OOXML_GENERATION_FORMATS else {
        "kind": "OOXMLStructuralValidation",
        "format": fmt,
        "path": str(path),
        "valid": path.exists() and path.is_file(),
        "requiredParts": [],
        "missingParts": [],
        "xmlErrors": [] if path.exists() and path.is_file() else ["artifact does not exist or is not a file"],
        "zipEntries": [],
    }

    roundtrip = {
        "requested": bool(getattr(args, "roundtrip", False)),
        "executed": False,
        "available": False,
        "status": "skipped",
        "outputRef": None,
        "error": None,
    }
    if getattr(args, "roundtrip", False):
        if not getattr(args, "policy_ok", False):
            print("error: office validate --roundtrip requires --policy-ok", file=sys.stderr)
            return 1
        lo = _libreoffice_path()
        roundtrip["available"] = lo is not None
        if not lo:
            roundtrip["status"] = "blocked"
            roundtrip["error"] = "LibreOffice/soffice not found on PATH"
        elif not path.exists() or not path.is_file():
            roundtrip["status"] = "blocked"
            roundtrip["error"] = "artifact does not exist or is not a file"
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = [lo, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, str(path)]
                completed = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180)
                expected = Path(tmpdir) / f"{path.stem}.pdf"
                roundtrip["executed"] = True
                roundtrip["status"] = "success" if completed.returncode == 0 and expected.exists() else "failure"
                roundtrip["outputRef"] = str(expected.name) if expected.exists() else None
                if completed.returncode != 0:
                    roundtrip["error"] = f"stdout={completed.stdout[-200:]!r}; stderr={completed.stderr[-200:]!r}"

    status = "success" if structural["valid"] and roundtrip["status"] in {"skipped", "success"} else "failure"
    plan_args = type(
        "Args",
        (),
        {
            "artifact_type": _artifact_type_for_format(fmt),
            "format": fmt,
            "title": path.stem or "Office Artifact",
            "workroom_id": getattr(args, "workroom_id", DEFAULT_WORKROOM_ID),
            "output_root": DEFAULT_OUTPUT_ROOT,
            "backend": "libreoffice",
            "mode": "local-headless",
            "execute": False,
            "downloads_root": DEFAULT_DOWNLOADS_ROOT,
            "template_root": DEFAULT_TEMPLATE_ROOT,
        },
    )()
    plan = _artifact_plan(plan_args, "validate", format_override=fmt)
    evidence = _build_evidence(
        plan=plan,
        operation="analyze",
        status=status,
        output_path=path if path.exists() and path.is_file() else None,
        source_refs=[_redact_home(str(path)) or str(path)],
        notes=f"structuralValid={structural['valid']}; roundtripStatus={roundtrip['status']}",
    )
    evidence_out = getattr(args, "evidence_out", None)
    if evidence_out:
        _write_json(evidence_out, evidence)

    result = {
        "type": "OfficeQualityGateResult",
        "status": status,
        "format": fmt,
        "path": _redact_home(str(path)),
        "structural": structural,
        "roundtrip": roundtrip,
        "evidenceOut": _redact_home(evidence_out) if evidence_out else None,
        "evidence": None if evidence_out else evidence,
    }
    return _print_json(result) if status == "success" else (_print_json(result) or 1)


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
        "qualityGate": validate_ooxml_artifact(path, suffix) if suffix in OOXML_GENERATION_FORMATS else None,
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
        "kind": payload.get("kind") if isinstance(payload, dict) else None,
        "type": payload.get("type") if isinstance(payload, dict) else None,
        "artifactId": office_artifact.get("artifactId") if isinstance(office_artifact, dict) else payload.get("artifactId"),
        "workroomId": office_artifact.get("workroomId") if isinstance(office_artifact, dict) else payload.get("workroomId"),
        "artifactType": office_artifact.get("artifactType") if isinstance(office_artifact, dict) else payload.get("artifactType"),
        "format": office_artifact.get("format") if isinstance(office_artifact, dict) else payload.get("format"),
        "evidenceRefs": office_artifact.get("evidenceRefs", []) if isinstance(office_artifact, dict) else payload.get("evidenceRefs", []),
    }
    return _print_json(summary)
