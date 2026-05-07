"""Workspace Operation Plane developer tooling commands."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_conformance_module():
    module_path = _repo_root() / "tools" / "sourceos_operation_conformance.py"
    spec = importlib.util.spec_from_file_location("sourceos_operation_conformance", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load conformance module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _validate_state_machine(path: Path, data: Dict[str, Any], errors: List[str]) -> None:
    operation = data.get("operation") or {}
    operation_status = operation.get("status")
    allowed = {
        "pending",
        "in_progress",
        "awaiting_decision",
        "blocked",
        "retrying",
        "completed",
        "failed",
        "cancelled",
    }
    if operation_status and operation_status not in allowed:
        errors.append(f"{path}: operation.status is unknown: {operation_status}")

    task_ids = set(operation.get("task_ids") or [])
    events = _as_list(data.get("event")) + list(data.get("events") or [])
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"{path}: event[{index}] must be an object")
            continue
        if event.get("operation_id") and event.get("operation_id") != operation.get("operation_id"):
            errors.append(f"{path}: event[{index}] operation_id mismatch")
        event_task_id = event.get("task_id")
        if event_task_id and task_ids and event_task_id not in task_ids:
            errors.append(f"{path}: event[{index}] task_id not listed in operation.task_ids: {event_task_id}")
        if not event.get("event_type"):
            errors.append(f"{path}: event[{index}] event_type is required")


def validate_fixture(args: argparse.Namespace) -> int:
    module = _load_conformance_module()
    fixture = Path(args.fixture).expanduser().resolve()
    if not fixture.exists():
        print(json.dumps({"type": "OperationFixtureValidation", "result": "fail", "errors": [f"missing fixture: {fixture}"]}, indent=2, sort_keys=True))
        return 1

    results = module.ValidationErrorSet()
    try:
        data = module.load_json(fixture)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"type": "OperationFixtureValidation", "result": "fail", "errors": [f"{fixture}: failed to parse JSON: {exc}"]}, indent=2, sort_keys=True))
        return 1

    module.validate_structural(fixture, data, results)
    _validate_state_machine(fixture, data, results.errors)

    if not args.structural_only:
        schemas_dir = Path(args.schemas_dir).expanduser().resolve() if args.schemas_dir else None
        module.optional_schema_validation(module.Paths(examples_dir=fixture.parent, schemas_dir=schemas_dir), [fixture], results)

    report = {
        "type": "OperationFixtureValidation",
        "fixture": str(fixture),
        "result": "pass" if results.ok() else "fail",
        "errors": results.errors,
        "warnings": results.warnings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if results.ok() else 1


def replay_fixture(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.force:
        print(json.dumps({"type": "OperationReplayFixture", "result": "fail", "errors": [f"output file exists: {output}; use --force to overwrite"]}, indent=2, sort_keys=True))
        return 1

    surface_prefix = args.surface.replace("-", "_")
    operation_id = f"op_{surface_prefix}_fixture_001"
    task_id = f"task_{surface_prefix}_fixture_001"
    artifact_id = f"artifact_{surface_prefix}_fixture_001"
    event_id = f"event_{surface_prefix}_fixture_001"
    payload = {
        "operation": {
            "schema_version": "0.1.0",
            "operation_id": operation_id,
            "operation_type": f"sourceos.{args.surface}.replay",
            "status": "completed",
            "idempotency_key": f"idem_{operation_id}",
            "task_ids": [task_id],
            "artifact_ids": [artifact_id],
            "decision_ids": [],
            "policy_gate_ids": [],
        },
        "task": {
            "schema_version": "0.1.0",
            "task_id": task_id,
            "operation_id": operation_id,
            "task_type": f"sourceos.{args.surface}.task",
            "status": "completed",
            "retryable": True,
            "idempotency_key": f"idem_{task_id}",
        },
        "event": {
            "schema_version": "0.1.0",
            "event_id": event_id,
            "event_type": f"{args.surface}.completed",
            "operation_id": operation_id,
            "task_id": task_id,
        },
        "artifact": {
            "schema_version": "0.1.0",
            "artifact_id": artifact_id,
            "artifact_type": "diagnostic_bundle",
            "created_by_operation_id": operation_id,
            "admission_state": "admitted",
            "activation_state": "active",
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"type": "OperationReplayFixture", "result": "pass", "surface": args.surface, "output": str(output)}, indent=2, sort_keys=True))
    return 0


def scaffold_adapter(args: argparse.Namespace) -> int:
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = {
        "terminal-command": {
            "adapter_type": "terminal-command",
            "command": ["bash", "-lc", "echo SourceOS operation adapter terminal skeleton"],
            "capture": {"stdout": True, "stderr": True, "exit_code": True},
        },
        "browser-capture": {
            "adapter_type": "browser-capture",
            "capture": {"network": True, "console": True, "dom_snapshot": True},
            "entrypoint": "https://example.local/workroom",
        },
        "local-agent-execution": {
            "adapter_type": "local-agent-execution",
            "agent_runtime": "sourceos-local-agent",
            "plan_ref": "urn:srcos:agent-plan:local-default",
            "collect": ["events", "artifacts", "policy-gates"],
        },
    }

    written: list[str] = []
    for name, payload in templates.items():
        path = out_dir / f"{name}.adapter.json"
        if path.exists() and not args.force:
            print(json.dumps({"type": "OperationAdapterScaffold", "result": "fail", "errors": [f"output file exists: {path}; use --force to overwrite"]}, indent=2, sort_keys=True))
            return 1
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        written.append(str(path))

    print(json.dumps({"type": "OperationAdapterScaffold", "result": "pass", "outputDir": str(out_dir), "files": written}, indent=2, sort_keys=True))
    return 0


def conformance(args: argparse.Namespace) -> int:
    module = _load_conformance_module()
    argv: list[str] = []
    if args.contracts_dir:
        argv.extend(["--contracts-dir", args.contracts_dir])
    if args.examples_dir:
        argv.extend(["--examples-dir", args.examples_dir])
    if args.schemas_dir:
        argv.extend(["--schemas-dir", args.schemas_dir])
    if args.structural_only:
        argv.append("--structural-only")
    return int(module.main(argv))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl operation", description="Workspace Operation Plane tooling")
    sub = parser.add_subparsers(dest="operation_command", required=True)

    validate_p = sub.add_parser("validate-fixture", help="Validate a Workspace Operation fixture JSON")
    validate_p.add_argument("fixture")
    validate_p.add_argument("--schemas-dir", default="../prophet-core-contracts/schemas")
    validate_p.add_argument("--structural-only", action="store_true", default=False)
    validate_p.set_defaults(func=validate_fixture)

    replay_p = sub.add_parser("replay-fixture", help="Generate a local replay fixture skeleton")
    replay_p.add_argument("output")
    replay_p.add_argument(
        "--surface",
        choices=["terminal-command", "browser-capture", "local-agent-execution"],
        default="terminal-command",
    )
    replay_p.add_argument("--force", action="store_true", default=False)
    replay_p.set_defaults(func=replay_fixture)

    scaffold_p = sub.add_parser("scaffold-adapter", help="Scaffold starter adapter skeleton files")
    scaffold_p.add_argument("output_dir")
    scaffold_p.add_argument("--force", action="store_true", default=False)
    scaffold_p.set_defaults(func=scaffold_adapter)

    conformance_p = sub.add_parser("conformance", help="Run fixture bundle conformance checks")
    conformance_p.add_argument("--contracts-dir", default=None)
    conformance_p.add_argument("--examples-dir", default="../prophet-core-contracts/examples/workspace-operation")
    conformance_p.add_argument("--schemas-dir", default="../prophet-core-contracts/schemas")
    conformance_p.add_argument("--structural-only", action="store_true", default=False)
    conformance_p.set_defaults(func=conformance)

    return parser


def operation_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
