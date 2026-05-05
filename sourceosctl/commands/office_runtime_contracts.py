"""SourceOS Office runtime contract record helpers.

These helpers project local SourceOS office evidence into the open Prophet
Platform office runtime records used by the WOPI/platform layer.  They do not
introduce closed-provider authority; imported/closed providers remain migration
or provenance concerns outside the local CLI write path.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


OFFICE_RUNTIME_CONTRACT_SCHEMAS = {
    "officeDocumentRecord": "https://socioprophet.dev/schemas/office/office_document_record.schema.json",
    "officeSessionRecord": "https://socioprophet.dev/schemas/office/office_session_record.schema.json",
    "officeVersionRecord": "https://socioprophet.dev/schemas/office/office_version_record.schema.json",
    "officeWritebackRecord": "https://socioprophet.dev/schemas/office/office_writeback_record.schema.json",
}


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_:." else "-" for ch in value)[:120]


def document_canonical_format(fmt: str) -> str:
    normalized = fmt.lower()
    if normalized in {"docx", "xlsx", "pptx"}:
        return "OOXML"
    if normalized in {"odt", "ods", "odp"}:
        return "ODF"
    if normalized == "pdf":
        return "PDF"
    return "MIXED"


def version_canonical_format(fmt: str) -> str:
    normalized = fmt.lower()
    if normalized in {"docx", "xlsx", "pptx"}:
        return "OOXML"
    if normalized in {"odt", "ods", "odp"}:
        return "ODF"
    if normalized == "pdf":
        return "PDF"
    if normalized == "md":
        return "MARKDOWN"
    if normalized == "txt":
        return "PLAIN_TEXT"
    return "MIXED"


def execution_backend(engine: str, mode: str) -> str:
    normalized = f"{engine}:{mode}".lower()
    if "collabora" in normalized:
        return "COLLABORA"
    if "libreoffice" in normalized:
        return "LIBREOFFICE"
    if "headless" in normalized:
        return "HEADLESS"
    if "sourceos" in normalized:
        return "SOURCEOS_NATIVE"
    if "manual" in normalized:
        return "MANUAL"
    return "OTHER_OPEN"


def editor_binding(engine: str, mode: str) -> str:
    normalized = f"{engine}:{mode}".lower()
    if "collabora" in normalized:
        return "COLLABORA"
    if "libreoffice" in normalized:
        return "LOCAL_LIBREOFFICE"
    if "headless" in normalized:
        return "HEADLESS"
    return "OTHER"


def capture_source(operation: str) -> str:
    if operation == "convert":
        return "CONVERSION"
    if operation == "generate":
        return "SYSTEM_WORKFLOW"
    return "LOCAL_SAVE"


def writeback_operation(operation: str) -> str:
    if operation == "convert":
        return "CONVERSION_SAVE"
    return "LOCAL_SAVE"


def build_office_runtime_contracts(*, plan: Dict[str, Any], evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build SourceOS-compatible office runtime records from local evidence.

    Returns None when there is no materialized artifact hash.  That keeps dry-run
    and failed conversions from pretending to have committed content.
    """

    artifact = plan.get("officeArtifact", {})
    artifact_hashes = evidence.get("artifactHashes") or []
    if not isinstance(artifact, dict) or not artifact_hashes:
        return None

    first_hash = artifact_hashes[0]
    content_hash = first_hash.get("sha256")
    if not isinstance(content_hash, str) or not content_hash.startswith("sha256:"):
        return None

    fmt = str(artifact.get("format") or evidence.get("format") or "json").lower()
    artifact_id = _safe_id(str(artifact.get("artifactId") or evidence.get("artifactId") or "office-artifact"))
    workroom_id = str(artifact.get("workroomId") or evidence.get("workroomId") or "workroom-local-default")
    storage_ref = str(artifact.get("storageRef") or evidence.get("storageRef") or f"sourceos-office://{workroom_id}/{artifact_id}.{fmt}")
    backend = artifact.get("backend", {}) if isinstance(artifact.get("backend"), dict) else {}
    engine = str(backend.get("engine") or "libreoffice")
    mode = str(backend.get("mode") or "local-headless")
    operation = str(evidence.get("operation") or "generate")
    captured_at = str(evidence.get("capturedAt"))

    version_id = f"office-version-{artifact_id}-0001"
    writeback_id = f"office-writeback-{artifact_id}-0001"
    session_id = f"office-session-{artifact_id}-local-cli"
    execution = execution_backend(engine, mode)

    document_record = {
        "document_id": artifact_id,
        "tenant_id": workroom_id,
        "storage_uri": storage_ref,
        "source_provider": "SOURCEOS",
        "current_format": fmt,
        "canonical_format": document_canonical_format(fmt),
        "permissions_ref": "policy://sourceos/office/local-guarded",
        "version_head": version_id,
        "editor_binding": editor_binding(engine, mode),
        "created_at": captured_at,
        "updated_at": captured_at,
    }

    session_record = {
        "session_id": session_id,
        "document_id": artifact_id,
        "editor_binding": editor_binding(engine, mode),
        "mode": "EDIT",
        "participants": [],
        "version_head": version_id,
        "status": "CLOSED",
        "created_at": captured_at,
        "updated_at": captured_at,
    }

    version_record = {
        "version_id": version_id,
        "document_id": artifact_id,
        "tenant_id": workroom_id,
        "version_number": 1,
        "content_ref": storage_ref,
        "content_hash": content_hash,
        "format": fmt,
        "canonical_format": version_canonical_format(fmt),
        "source_provider": "SOURCEOS",
        "execution_backend": execution,
        "capture_source": capture_source(operation),
        "created_by_ref": "sourceosctl://office/local-cli",
        "writeback_ref": f"writeback://office/{writeback_id}",
        "policy_decision_ref": "policy://sourceos/office/local-guarded",
        "receipt_refs": [],
        "semantic_unit_refs": [],
        "created_at": captured_at,
        "labels": {
            "sourceos.surface": "office-plane",
            "sourceos.operation": operation,
        },
    }

    writeback_record = {
        "writeback_id": writeback_id,
        "document_id": artifact_id,
        "session_id": session_id,
        "operation": writeback_operation(operation),
        "status": "COMMITTED",
        "base_version_id": "office-version-none-0000",
        "result_version_id": version_id,
        "actor_ref": "sourceosctl://office/local-cli",
        "source": "LOCAL_CLI",
        "execution_backend": execution,
        "content_ref": storage_ref,
        "content_hash": content_hash,
        "policy_decision_ref": "policy://sourceos/office/local-guarded",
        "receipt_ref": f"receipt://sourceos/office/{artifact_id}/0001",
        "requested_at": captured_at,
        "committed_at": captured_at,
        "labels": {
            "sourceos.hot_path": "local-cli",
            "sourceos.operation": operation,
        },
    }

    return {
        "schemas": OFFICE_RUNTIME_CONTRACT_SCHEMAS,
        "officeDocumentRecord": document_record,
        "officeSessionRecord": session_record,
        "officeVersionRecord": version_record,
        "officeWritebackRecord": writeback_record,
    }
