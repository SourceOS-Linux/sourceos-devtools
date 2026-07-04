"""Argument parser for the SourceOS Portable AI Kit command group."""

from __future__ import annotations

import argparse

from sourceosctl.commands import portable_ai, portable_ai_byom, portable_ai_runtime

SURFACES = ["turtleterm", "agent-term", "bearbrowser", "local-web", "anythingllm-adapter"]
BYOM_TASK_CLASSES = [
    "operator-selected", "router", "triage", "summarization", "rewrite", "office-assist",
    "artifact-drafting", "coding-assist", "repo-triage", "privacy-first-chat", "offline-fallback",
    "operator-assist", "evidence-inspection", "workroom-local", "field-workroom",
]


def add_runtime_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("target_root", help="Target portable root")
    parser.add_argument("--provider", default=portable_ai_runtime.DEFAULT_PROVIDER, choices=portable_ai_runtime.SUPPORTED_PROVIDERS)
    parser.add_argument("--host", default=portable_ai_runtime.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=portable_ai_runtime.DEFAULT_PORT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl portable-ai", description="SourceOS Portable AI Kit helpers")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    profiles_p = sub.add_parser("profiles", help="List built-in portable AI profiles")
    profiles_p.set_defaults(func=portable_ai.profiles)

    preflight_p = sub.add_parser("preflight", help="Inspect a portable root target without changing it")
    preflight_p.add_argument("target_root")
    preflight_p.add_argument("--profile", default="laptop-safe", choices=sorted(portable_ai.PORTABLE_PROFILES))
    preflight_p.add_argument("--benchmark", action="store_true", default=False)
    preflight_p.set_defaults(func=portable_ai.preflight)

    prepare_p = sub.add_parser("prepare", help="Render or execute portable root materialization")
    prepare_p.add_argument("target_root")
    prepare_p.add_argument("--profile", default="laptop-safe", choices=sorted(portable_ai.PORTABLE_PROFILES))
    prepare_p.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    prepare_p.add_argument("--execute", action="store_true", default=False)
    prepare_p.add_argument("--policy-ok", action="store_true", default=False)
    prepare_p.add_argument("--evidence-out", default=None)
    prepare_p.set_defaults(func=portable_ai.prepare)

    byom_p = sub.add_parser("byom", help="Bring-your-own local model helpers")
    byom_sub = byom_p.add_subparsers(dest="byom_command", metavar="<subcommand>")
    byom_sub.required = True
    byom_verify_p = byom_sub.add_parser("verify", help="Hash and verify a local model file")
    byom_verify_p.add_argument("target_root")
    byom_verify_p.add_argument("model_file")
    byom_verify_p.add_argument("--name", default=None)
    byom_verify_p.add_argument("--display-name", default=None)
    byom_verify_p.add_argument("--pack-id", default=None)
    byom_verify_p.add_argument("--license-ref", default="operator-attestation-required")
    byom_verify_p.add_argument("--source-note", default=None)
    byom_verify_p.add_argument("--task-class", action="append", choices=BYOM_TASK_CLASSES)
    byom_verify_p.add_argument("--copy", action="store_true", default=False)
    byom_verify_p.add_argument("--dry-run", action="store_true", default=True, dest="dry_run")
    byom_verify_p.add_argument("--execute", action="store_true", default=False)
    byom_verify_p.add_argument("--policy-ok", action="store_true", default=False)
    byom_verify_p.add_argument("--evidence-out", default=None)
    byom_verify_p.set_defaults(func=portable_ai_byom.verify)

    start_p = sub.add_parser("start-plan", help="Render a local runtime launch plan")
    add_runtime_common(start_p)
    start_p.add_argument("--surface", default="turtleterm", choices=SURFACES)
    start_p.add_argument("--model", default=None)
    start_p.set_defaults(func=portable_ai_runtime.start_plan)

    stop_p = sub.add_parser("stop-plan", help="Render a local runtime stop plan")
    add_runtime_common(stop_p)
    stop_p.set_defaults(func=portable_ai_runtime.stop_plan)

    inspect_p = sub.add_parser("inspect", help="Inspect portable root layout state")
    inspect_p.add_argument("target_root")
    inspect_p.set_defaults(func=portable_ai.inspect)

    evidence_p = sub.add_parser("evidence", help="Portable AI evidence helpers")
    evidence_sub = evidence_p.add_subparsers(dest="evidence_command", metavar="<subcommand>")
    evidence_sub.required = True
    evidence_inspect_p = evidence_sub.add_parser("inspect", help="Inspect portable AI evidence JSON")
    evidence_inspect_p.add_argument("path")
    evidence_inspect_p.set_defaults(func=portable_ai.evidence_inspect)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
