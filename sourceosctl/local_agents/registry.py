"""Load SourceOS local-agent registry declarations."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalAgentRecord:
    """Normalized local-agent registry record."""

    name: str
    label: str
    scope: str
    runtime: str
    container_name: str
    runtime_image: str
    source_image: str
    podman_connection: str
    authfile: str
    user_plist: str
    legacy_system_plist: str
    log_dir: str
    app_log: str
    raw: dict[str, Any]


def registry_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent


def registry_files(base: pathlib.Path | None = None) -> list[pathlib.Path]:
    root = base or registry_dir()
    return sorted(p for p in root.glob("*.json") if p.name != "schema.json")


def _require(payload: dict[str, Any], dotted: str) -> Any:
    cursor: Any = payload
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            raise ValueError(f"missing required field: {dotted}")
        cursor = cursor[part]
    return cursor


def normalize(payload: dict[str, Any]) -> LocalAgentRecord:
    """Normalize a registry declaration into the CLI-compatible shape."""
    return LocalAgentRecord(
        name=str(_require(payload, "name")),
        label=str(_require(payload, "label")),
        scope=str(_require(payload, "scope")),
        runtime=str(_require(payload, "runtime")),
        container_name=str(_require(payload, "container.name")),
        runtime_image=str(_require(payload, "container.runtimeImage")),
        source_image=str(_require(payload, "container.sourceImage")),
        podman_connection=str(_require(payload, "podman.connection")),
        authfile=str(_require(payload, "auth.authfile")),
        user_plist=str(_require(payload, "macos.launchd.plist")),
        legacy_system_plist=str(_require(payload, "macos.launchd.legacySystemPlist")),
        log_dir=str(_require(payload, "logs.directory")),
        app_log=str(_require(payload, "logs.app")),
        raw=payload,
    )


def load_record(path: pathlib.Path) -> LocalAgentRecord:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"registry file must contain an object: {path}")
    return normalize(payload)


def load_records(base: pathlib.Path | None = None) -> dict[str, LocalAgentRecord]:
    records: dict[str, LocalAgentRecord] = {}
    for path in registry_files(base):
        record = load_record(path)
        if record.name in records:
            raise ValueError(f"duplicate local-agent declaration: {record.name}")
        records[record.name] = record
    return records


def load_record_or_error(name: str, base: pathlib.Path | None = None) -> LocalAgentRecord:
    records = load_records(base)
    try:
        return records[name]
    except KeyError as exc:
        known = ", ".join(sorted(records)) or "<none>"
        raise SystemExit(f"unknown local agent: {name}; known agents: {known}") from exc
