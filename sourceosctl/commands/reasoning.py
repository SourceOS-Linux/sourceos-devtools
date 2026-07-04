"""Read-only Superconscious / SourceOS reasoning artifact helpers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_CANONICAL = [
    "reasoning-events.sourceos.jsonl",
    "reasoning-run.sourceos.json",
    "reasoning-receipt.json",
    "reasoning-replay-plan.json",
    "reasoning-benchmark.json",
]
VALID_REPLAY_CLASSES = {"exact", "best-effort", "evidence-only", "non-replayable-side-effect"}


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_run_dir(run_dir: Path) -> Dict[str, Any]:
    run_dir = run_dir.resolve()
    errors: List[str] = []

    for artifact in REQUIRED_CANONICAL:
        if not (run_dir / artifact).exists():
            errors.append(f"missing canonical artifact: {artifact}")

    if errors:
        return {"type": "ReasoningValidation", "result": "fail", "runDir": str(run_dir), "errors": errors}

    events = _load_jsonl(run_dir / "reasoning-events.sourceos.jsonl")
    reasoning_run = _load_json(run_dir / "reasoning-run.sourceos.json")
    receipt = _load_json(run_dir / "reasoning-receipt.json")
    replay = _load_json(run_dir / "reasoning-replay-plan.json")
    benchmark = _load_json(run_dir / "reasoning-benchmark.json")

    run_id = reasoning_run.get("id")
    if reasoning_run.get("type") != "ReasoningRun":
        errors.append("reasoning-run.sourceos.json type must be ReasoningRun")
    if reasoning_run.get("safeTrace", {}).get("mode") != "operational-trace-only":
        errors.append("safe trace mode must be operational-trace-only")
    if reasoning_run.get("safeTrace", {}).get("rawPrivateReasoning") != "not-collected":
        errors.append("raw private reasoning must be not-collected")

    for index, event in enumerate(events, start=1):
        if event.get("type") != "ReasoningEvent":
            errors.append(f"event line {index} type must be ReasoningEvent")
        if event.get("runRef") != run_id:
            errors.append(f"event line {index} runRef mismatch")
        if event.get("traceLevel") == "denied":
            errors.append(f"event line {index} must not emit denied trace content")

    if receipt.get("type") != "ReasoningReceipt" or receipt.get("runRef") != run_id:
        errors.append("reasoning receipt mismatch")
    if replay.get("type") != "ReasoningReplayPlan" or replay.get("runRef") != run_id:
        errors.append("reasoning replay plan mismatch")
    if replay.get("replayClass") not in VALID_REPLAY_CLASSES:
        errors.append("invalid replay class")
    if benchmark.get("type") != "ReasoningBenchmark" or benchmark.get("runRef") != run_id:
        errors.append("reasoning benchmark mismatch")
    if benchmark.get("passed") is not True:
        errors.append("reasoning benchmark must pass")

    return {
        "type": "ReasoningValidation",
        "result": "pass" if not errors else "fail",
        "runDir": str(run_dir),
        "runId": run_id,
        "status": reasoning_run.get("status"),
        "eventCount": len(events),
        "replayClass": replay.get("replayClass"),
        "benchmarkSuite": benchmark.get("suite"),
        "benchmarkPassed": benchmark.get("passed"),
        "safeTraceMode": reasoning_run.get("safeTrace", {}).get("mode"),
        "rawPrivateReasoning": reasoning_run.get("safeTrace", {}).get("rawPrivateReasoning"),
        "errors": errors,
    }


def validate_cmd(args) -> int:
    report = validate_run_dir(Path(args.run_dir))
    _print_json(report)
    return 0 if report["result"] == "pass" else 1


def inspect_cmd(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    report = validate_run_dir(run_dir)
    if report["result"] != "pass" and not args.allow_invalid:
        _print_json(report)
        return 1

    reasoning_run = _load_json(run_dir / "reasoning-run.sourceos.json")
    replay = _load_json(run_dir / "reasoning-replay-plan.json")
    benchmark = _load_json(run_dir / "reasoning-benchmark.json")
    events = _load_jsonl(run_dir / "reasoning-events.sourceos.jsonl")

    return _print_json(
        {
            "type": "ReasoningInspection",
            "runId": reasoning_run.get("id"),
            "status": reasoning_run.get("status"),
            "task": reasoning_run.get("task"),
            "agentRef": reasoning_run.get("agentRef"),
            "workspaceRef": reasoning_run.get("workspaceRef"),
            "safeTrace": reasoning_run.get("safeTrace"),
            "replayClass": replay.get("replayClass"),
            "benchmark": {
                "suite": benchmark.get("suite"),
                "passed": benchmark.get("passed"),
                "assertions": benchmark.get("assertions", []),
            },
            "eventTimeline": [
                {
                    "id": event.get("id"),
                    "eventType": event.get("eventType"),
                    "summary": event.get("summary"),
                    "traceLevel": event.get("traceLevel"),
                    "trustLevel": event.get("trustLevel"),
                }
                for event in events
            ],
        }
    )


def replay_plan_cmd(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    return _print_json(_load_json(run_dir / "reasoning-replay-plan.json"))


def events_cmd(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    events = _load_jsonl(run_dir / "reasoning-events.sourceos.jsonl")
    return _print_json({"type": "ReasoningEvents", "runDir": str(run_dir), "events": events})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl reasoning", description="Inspect and validate SourceOS reasoning artifacts")
    sub = parser.add_subparsers(dest="reasoning_command", required=True)

    validate_p = sub.add_parser("validate", help="Validate a Superconscious/SourceOS reasoning run directory")
    validate_p.add_argument("run_dir")
    validate_p.set_defaults(func=validate_cmd)

    inspect_p = sub.add_parser("inspect", help="Inspect a reasoning run directory")
    inspect_p.add_argument("run_dir")
    inspect_p.add_argument("--allow-invalid", action="store_true", default=False)
    inspect_p.set_defaults(func=inspect_cmd)

    replay_p = sub.add_parser("replay-plan", help="Print the reasoning replay plan")
    replay_p.add_argument("run_dir")
    replay_p.set_defaults(func=replay_plan_cmd)

    events_p = sub.add_parser("events", help="Print reasoning events")
    events_p.add_argument("run_dir")
    events_p.set_defaults(func=events_cmd)
    return parser


def reasoning_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
