#!/usr/bin/env python3
"""SourceOS Workspace Operation conformance runner.

Validates Workspace Operation Plane fixture bundles from prophet-core-contracts or
from a local adapter repo. The runner uses only stdlib for structural checks and
optionally enables full JSON Schema validation when the `jsonschema` package is
installed.

Default repo layout assumes:
  ~/dev/sourceos-devtools
  ~/dev/prophet-core-contracts

Usage:
  python3 tools/sourceos_operation_conformance.py \
    --contracts-dir ../prophet-core-contracts

  python3 tools/sourceos_operation_conformance.py \
    --examples-dir ../prophet-core-contracts/examples/workspace-operation \
    --schemas-dir ../prophet-core-contracts/schemas
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:  # optional dependency, intentionally not required for basic checks
    import jsonschema  # type: ignore
except Exception:  # noqa: BLE001
    jsonschema = None  # type: ignore


@dataclass(frozen=True)
class Paths:
    examples_dir: Path
    schemas_dir: Path | None


class ValidationErrorSet:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self) -> bool:
        return not self.errors


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("top-level JSON value must be an object")
    return loaded


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def validate_structural(path: Path, data: dict[str, Any], results: ValidationErrorSet) -> None:
    operation = data.get("operation")
    if not isinstance(operation, dict):
        results.error(f"{path}: missing operation object")
        return

    op_id = operation.get("operation_id")
    if not op_id:
        results.error(f"{path}: operation.operation_id is required")

    if operation.get("schema_version") != "0.1.0":
        results.error(f"{path}: operation.schema_version must be 0.1.0")

    if not operation.get("operation_type"):
        results.error(f"{path}: operation.operation_type is required")

    if not operation.get("idempotency_key"):
        results.error(f"{path}: operation.idempotency_key is required")

    task_ids = set(operation.get("task_ids", []))
    artifact_ids = set(operation.get("artifact_ids", []))
    decision_ids = set(operation.get("decision_ids", []))
    policy_gate_ids = set(operation.get("policy_gate_ids", []))

    task_objects = as_list(data.get("task")) + list(data.get("tasks", []))
    artifact_objects = as_list(data.get("artifact")) + list(data.get("artifacts", []))
    decision_objects = as_list(data.get("decision")) + list(data.get("decisions", []))
    gate_objects = as_list(data.get("policy_gate")) + list(data.get("policy_gates", []))

    seen_task_ids = {task.get("task_id") for task in task_objects if isinstance(task, dict)}
    missing_tasks = task_ids - seen_task_ids
    if missing_tasks:
        results.error(f"{path}: operation.task_ids missing objects: {sorted(missing_tasks)}")

    seen_artifact_ids = {artifact.get("artifact_id") for artifact in artifact_objects if isinstance(artifact, dict)}
    missing_artifacts = artifact_ids - seen_artifact_ids
    if missing_artifacts:
        results.error(f"{path}: operation.artifact_ids missing objects: {sorted(missing_artifacts)}")

    seen_decision_ids = {decision.get("decision_id") for decision in decision_objects if isinstance(decision, dict)}
    missing_decisions = decision_ids - seen_decision_ids
    if missing_decisions:
        results.error(f"{path}: operation.decision_ids missing objects: {sorted(missing_decisions)}")

    seen_gate_ids = {gate.get("gate_id") for gate in gate_objects if isinstance(gate, dict)}
    missing_gates = policy_gate_ids - seen_gate_ids
    if missing_gates:
        results.error(f"{path}: operation.policy_gate_ids missing objects: {sorted(missing_gates)}")

    for task in task_objects:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if task.get("operation_id") != op_id:
            results.error(f"{path}: task {task_id} operation_id mismatch")
        if task_id and task_ids and task_id not in task_ids:
            results.error(f"{path}: task {task_id} not listed in operation.task_ids")
        if task.get("retryable") and not task.get("idempotency_key"):
            results.error(f"{path}: retryable task {task_id} lacks idempotency_key")
        if task.get("status") == "failed" and task.get("retryable") and not task.get("idempotency_key"):
            results.error(f"{path}: failed retryable task {task_id} lacks idempotency_key")

    for artifact in artifact_objects:
        if not isinstance(artifact, dict):
            continue
        artifact_id = artifact.get("artifact_id")
        if artifact_id and artifact_ids and artifact_id not in artifact_ids:
            results.error(f"{path}: artifact {artifact_id} not listed in operation.artifact_ids")
        if artifact.get("activation_state") == "active" and artifact.get("admission_state") not in {"admitted", "activated"}:
            results.error(f"{path}: artifact {artifact_id} active before admission")
        if artifact.get("admission_state") == "quarantined" and artifact.get("activation_state") == "active":
            results.error(f"{path}: artifact {artifact_id} is quarantined but active")

    for decision in decision_objects:
        if not isinstance(decision, dict):
            continue
        decision_id = decision.get("decision_id")
        if decision_id and decision_ids and decision_id not in decision_ids:
            results.error(f"{path}: decision {decision_id} not listed in operation.decision_ids")
        if decision.get("status") == "pending" and not decision.get("options"):
            results.error(f"{path}: pending decision {decision_id} has no options")

    for gate in gate_objects:
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("gate_id")
        if gate_id and policy_gate_ids and gate_id not in policy_gate_ids:
            results.error(f"{path}: policy gate {gate_id} not listed in operation.policy_gate_ids")
        if gate.get("status") in {"blocking", "requires_decision", "requires_admin"}:
            if not gate.get("responsible_actor"):
                results.error(f"{path}: blocking gate {gate_id} lacks responsible_actor")
            if not gate.get("remediation_options"):
                results.error(f"{path}: blocking gate {gate_id} lacks remediation_options")

    if operation.get("status") == "awaiting_decision" and not decision_ids:
        results.error(f"{path}: awaiting_decision operation lacks decision_ids")

    if operation.get("status") == "blocked" and not policy_gate_ids:
        results.error(f"{path}: blocked operation lacks policy_gate_ids")


def optional_schema_validation(paths: Paths, files: Iterable[Path], results: ValidationErrorSet) -> None:
    if paths.schemas_dir is None:
        results.warning("schema validation skipped: no schemas directory supplied")
        return
    if jsonschema is None:
        results.warning("schema validation skipped: install jsonschema for full checks")
        return

    schema_paths = {
        "operation": paths.schemas_dir / "workspace-operation.schema.json",
        "task_event": paths.schemas_dir / "operation-task-event.schema.json",
        "artifact": paths.schemas_dir / "artifact-admission.schema.json",
        "decision_policy": paths.schemas_dir / "decision-policy-adapter.schema.json",
    }
    schemas: dict[str, dict[str, Any]] = {}
    for name, schema_path in schema_paths.items():
        if not schema_path.exists():
            results.error(f"missing schema file: {schema_path}")
            return
        schemas[name] = load_json(schema_path)

    for fixture_path in files:
        data = load_json(fixture_path)
        objects: list[tuple[str, dict[str, Any]]] = []
        if isinstance(data.get("operation"), dict):
            objects.append(("operation", data["operation"]))
        for task in as_list(data.get("task")) + list(data.get("tasks", [])):
            if isinstance(task, dict):
                objects.append(("task_event", task))
        for event in as_list(data.get("event")) + list(data.get("events", [])):
            if isinstance(event, dict):
                objects.append(("task_event", event))
        for artifact in as_list(data.get("artifact")) + list(data.get("artifacts", [])):
            if isinstance(artifact, dict):
                objects.append(("artifact", artifact))
        for gate in as_list(data.get("policy_gate")) + list(data.get("policy_gates", [])):
            if isinstance(gate, dict):
                objects.append(("decision_policy", gate))
        for decision in as_list(data.get("decision")) + list(data.get("decisions", [])):
            if isinstance(decision, dict):
                objects.append(("decision_policy", decision))
        if isinstance(data.get("diagnostic_bundle"), dict):
            objects.append(("decision_policy", data["diagnostic_bundle"]))

        for schema_name, obj in objects:
            try:
                jsonschema.validate(instance=obj, schema=schemas[schema_name])  # type: ignore[union-attr]
            except Exception as exc:  # noqa: BLE001
                obj_id = obj.get("operation_id") or obj.get("task_id") or obj.get("artifact_id") or obj.get("decision_id") or obj.get("gate_id") or obj.get("diagnostic_bundle_id")
                results.error(f"{fixture_path}: schema validation failed for {schema_name}:{obj_id}: {exc}")


def resolve_paths(args: argparse.Namespace) -> Paths:
    if args.contracts_dir:
        contracts = Path(args.contracts_dir).expanduser().resolve()
        return Paths(
            examples_dir=contracts / "examples" / "workspace-operation",
            schemas_dir=contracts / "schemas",
        )
    examples_dir = Path(args.examples_dir).expanduser().resolve()
    schemas_dir = Path(args.schemas_dir).expanduser().resolve() if args.schemas_dir else None
    return Paths(examples_dir=examples_dir, schemas_dir=schemas_dir)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Workspace Operation Plane fixtures")
    parser.add_argument("--contracts-dir", help="Path to prophet-core-contracts checkout")
    parser.add_argument("--examples-dir", default="../prophet-core-contracts/examples/workspace-operation")
    parser.add_argument("--schemas-dir", default="../prophet-core-contracts/schemas")
    parser.add_argument("--structural-only", action="store_true", help="Skip optional JSON Schema validation")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    paths = resolve_paths(args)
    results = ValidationErrorSet()

    if not paths.examples_dir.exists():
        print(f"missing examples directory: {paths.examples_dir}", file=sys.stderr)
        return 1

    files = sorted(paths.examples_dir.glob("*.json"))
    if not files:
        print(f"no fixtures found in {paths.examples_dir}", file=sys.stderr)
        return 1

    for path in files:
        try:
            data = load_json(path)
        except Exception as exc:  # noqa: BLE001
            results.error(f"{path}: failed to parse JSON: {exc}")
            continue
        validate_structural(path, data, results)

    if not args.structural_only:
        optional_schema_validation(paths, files, results)

    for warning in results.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if not results.ok():
        print("Operation conformance validation failed:", file=sys.stderr)
        for error in results.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(files)} Workspace Operation fixture(s) from {paths.examples_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
