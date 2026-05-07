"""Argument parser for the SourceOS Portable AI Kit command group."""

from __future__ import annotations

import argparse

from sourceosctl.commands import portable_ai, portable_ai_byom, portable_ai_runtime


SURFACES = [
    "turtleterm",
    "agent-term",
    "bearbrowser",
    "local-web",
    "anythingllm-adapter",
]

BYOM_TASK_CLASSES = [
    "operator-selected",
    "router",
    "triage",
    "summarization",
    "rewrite",
    "office-assist",
    "artifact-drafting",
    "coding-assist",
    "repo-triage",
    "privacy-first-chat",
    "offline-fallback",
    "operator-assist",
    "evidence-inspection",
    "workroom-local",
    "field-workroom",
]


def add_runtime_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("target_root", help="Target USB/SSD portable root")
    p.add_argument(
        "--provider",
        default=portable_ai_runtime.DEFAULT_PROVIDER,
        choices=portable_ai_runtime.SUPPORTED_PROVIDERS,
        help="Local runtime provider class",
    )
    p.add_argument("--host", default=portable_ai_runtime.DEFAULT_HOST, help="Loopback host bind address")
    p.add_argument("--port", type=int, default=portable_ai_runtime.DEFAULT_PORT, help="Local runtime port")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sourceosctl portable-ai",
        description="SourceOS Portable AI Kit helpers (dry-run / evidence-first surface)",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    profiles_p = sub.add_parser("profiles", help="List built-in portable AI profiles")
    profiles_p.set_defaults(func=portable_ai.profiles)

    preflight_p = sub.add_parser(
        "preflight",
        help="Inspect a portable root target without mutating it",
    )
    preflight_p.add_argument("target_root", help="Target USB/SSD portable root")
    preflight_p.add_argument(
        "--benchmark",
        action="store_true",
        default=False,
        help="Reserve flag for future read/write benchmark",
    )
    preflight_p.set_defaults(func=portable_ai.preflight)

    prepare_p = sub.add_parser(
        "prepare",
        help="Render or execute portable root materialization",
    )
    prepare_p.add_argument("target_root", help="Target USB/SSD portable root")
    prepare_p.add_argument(
        "--profile",
        default="laptop-safe",
        choices=sorted(portable_ai.PORTABLE_PROFILES),
        help="Portable profile",
    )
    prepare_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Render plan without writing files",
    )
    prepare_p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Create declared portable-root directories and manifest",
    )
    prepare_p.add_argument(
        "--policy-ok",
        action="store_true",
        default=False,
        help="Confirm policy/operator approval for materialization",
    )
    prepare_p.add_argument("--evidence-out", default=None, help="Optional evidence JSON path")
    prepare_p.set_defaults(func=portable_ai.prepare)

    byom_p = sub.add_parser("byom", help="Bring-your-own local model helpers")
    byom_sub = byom_p.add_subparsers(dest="byom_command", metavar="<subcommand>")
    byom_sub.required = True
    byom_verify_p = byom_sub.add_parser(
        "verify",
        help="Hash and verify a local model file, optionally writing a ModelCarryPack manifest",
    )
    byom_verify_p.add_argument("target_root", help="Prepared Portable AI Kit root")
    byom_verify_p.add_argument("model_file", help="Local model file to verify; no download is performed")
    byom_verify_p.add_argument("--name", default=None, help="Short model/pack slug")
    byom_verify_p.add_argument("--display-name", default=None, help="Display name for the model pack")
    byom_verify_p.add_argument("--pack-id", default=None, help="Optional full model-carry-pack URN")
    byom_verify_p.add_argument(
        "--license-ref",
        default="operator-attestation-required",
        help="License or attestation reference for the operator-supplied file",
    )
    byom_verify_p.add_argument("--source-note", default=None, help="Optional local provenance note")
    byom_verify_p.add_argument(
        "--task-class",
        action="append",
        choices=BYOM_TASK_CLASSES,
        help="Allowed task class for this BYOM model; may be repeated",
    )
    byom_verify_p.add_argument(
        "--copy",
        action="store_true",
        default=False,
        help="Copy the local model file into target_root/models/blobs when executing",
    )
    byom_verify_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Render verification plan without writing manifest or copying model",
    )
    byom_verify_p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Write BYOM ModelCarryPack manifest and optionally copy the file",
    )
    byom_verify_p.add_argument(
        "--policy-ok",
        action="store_true",
        default=False,
        help="Confirm policy/operator approval for BYOM manifest materialization",
    )
    byom_verify_p.add_argument("--evidence-out", default=None, help="Optional evidence JSON path")
    byom_verify_p.set_defaults(func=portable_ai_byom.verify)

    start_p = sub.add_parser(
        "start-plan",
        help="Render a local runtime/surface launch plan without starting daemons",
    )
    add_runtime_common(start_p)
    start_p.add_argument(
        "--surface",
        default="turtleterm",
        choices=SURFACES,
        help="Launch surface",
    )
    start_p.add_argument("--model", default=None, help="Optional pack id, display name, or model name to select")
    start_p.set_defaults(func=portable_ai_runtime.start_plan)

    stop_p = sub.add_parser(
        "stop-plan",
        help="Render a local runtime teardown plan without killing processes",
    )
    add_runtime_common(stop_p)
    stop_p.set_defaults(func=portable_ai_runtime.stop_plan)

    inspect_p = sub.add_parser("inspect", help="Inspect portable root layout state")
    inspect_p.add_argument("target_root", help="Target USB/SSD portable root")
    inspect_p.set_defaults(func=portable_ai.inspect)

    evidence_p = sub.add_parser("evidence", help="Portable AI evidence helpers")
    evidence_sub = evidence_p.add_subparsers(dest="evidence_command", metavar="<subcommand>")
    evidence_sub.required = True
    evidence_inspect_p = evidence_sub.add_parser("inspect", help="Inspect portable AI evidence JSON")
    evidence_inspect_p.add_argument("path", help="Evidence JSON path")
    evidence_inspect_p.set_defaults(func=portable_ai.evidence_inspect)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
