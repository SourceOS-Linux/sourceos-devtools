"""sourceosctl CLI entry point."""

import argparse
import sys

from sourceosctl import __version__
from sourceosctl.commands import (
    doctor,
    profiles,
    nlboot,
    release,
    fingerprint,
    ai,
    agents,
    local_model,
    agent_machine,
    office,
)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sourceosctl",
        description="SourceOS developer and AI operator CLI (read-only / dry-run surface)",
    )
    parser.add_argument(
        "--version", action="version", version=f"sourceosctl {__version__}"
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # --- doctor ---
    doctor_p = sub.add_parser("doctor", help="Run environment health checks")
    doctor_p.set_defaults(func=doctor.run)

    # --- profiles ---
    profiles_p = sub.add_parser("profiles", help="Profile management")
    profiles_sub = profiles_p.add_subparsers(dest="profiles_command", metavar="<subcommand>")
    profiles_sub.required = True
    profiles_list_p = profiles_sub.add_parser("list", help="List available profiles")
    profiles_list_p.set_defaults(func=profiles.list_profiles)

    # --- nlboot ---
    nlboot_p = sub.add_parser("nlboot", help="NLBoot operator helpers")
    nlboot_sub = nlboot_p.add_subparsers(dest="nlboot_command", metavar="<subcommand>")
    nlboot_sub.required = True
    nlboot_evidence_p = nlboot_sub.add_parser("evidence", help="NLBoot evidence helpers")
    nlboot_evidence_sub = nlboot_evidence_p.add_subparsers(
        dest="nlboot_evidence_command", metavar="<subcommand>"
    )
    nlboot_evidence_sub.required = True
    nlboot_inspect_p = nlboot_evidence_sub.add_parser(
        "inspect", help="Inspect a NLBoot evidence file"
    )
    nlboot_inspect_p.add_argument("path", help="Path to NLBoot evidence JSON file")
    nlboot_inspect_p.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Validate the evidence file against its bundled JSON Schema",
    )
    nlboot_inspect_p.set_defaults(func=nlboot.inspect_evidence)

    nlboot_validate_p = nlboot_evidence_sub.add_parser(
        "validate", help="Validate a NLBoot evidence file against its bundled schema"
    )
    nlboot_validate_p.add_argument("path", help="Path to NLBoot evidence JSON file")
    nlboot_validate_p.set_defaults(func=nlboot.validate_evidence)

    # --- release ---
    release_p = sub.add_parser("release", help="Release artifact inspection")
    release_sub = release_p.add_subparsers(dest="release_command", metavar="<subcommand>")
    release_sub.required = True
    release_inspect_p = release_sub.add_parser("inspect", help="Inspect a release artifact")
    release_inspect_p.add_argument("path", help="Path to release artifact JSON file")
    release_inspect_p.set_defaults(func=release.inspect)

    release_inspect_archive_p = release_sub.add_parser(
        "inspect-archive",
        help="Inspect a NLBoot release archive directory for required files",
    )
    release_inspect_archive_p.add_argument(
        "path", help="Path to unpacked NLBoot release archive directory"
    )
    release_inspect_archive_p.set_defaults(func=release.inspect_archive)

    # --- fingerprint ---
    fingerprint_p = sub.add_parser("fingerprint", help="Environment fingerprint utilities")
    fingerprint_sub = fingerprint_p.add_subparsers(
        dest="fingerprint_command", metavar="<subcommand>"
    )
    fingerprint_sub.required = True
    fingerprint_collect_p = fingerprint_sub.add_parser(
        "collect", help="Collect environment fingerprint (dry-run only)"
    )
    fingerprint_collect_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print what would be collected without writing to disk (default: True)",
    )
    fingerprint_collect_p.set_defaults(func=fingerprint.collect)

    # --- ai ---
    ai_p = sub.add_parser("ai", help="AI operator utilities")
    ai_sub = ai_p.add_subparsers(dest="ai_command", metavar="<subcommand>")
    ai_sub.required = True
    ai_labs_p = ai_sub.add_parser("labs", help="AI lab helpers")
    ai_labs_sub = ai_labs_p.add_subparsers(dest="ai_labs_command", metavar="<subcommand>")
    ai_labs_sub.required = True
    ai_labs_list_p = ai_labs_sub.add_parser("list", help="List available AI labs")
    ai_labs_list_p.set_defaults(func=ai.list_labs)

    # --- agents ---
    agents_p = sub.add_parser("agents", help="Agent sandbox helpers")
    agents_sub = agents_p.add_subparsers(dest="agents_command", metavar="<subcommand>")
    agents_sub.required = True
    agents_sandbox_p = agents_sub.add_parser("sandbox", help="Agent sandbox management")
    agents_sandbox_sub = agents_sandbox_p.add_subparsers(
        dest="agents_sandbox_command", metavar="<subcommand>"
    )
    agents_sandbox_sub.required = True
    agents_sandbox_plan_p = agents_sandbox_sub.add_parser(
        "plan", help="Plan agent sandbox (dry-run only)"
    )
    agents_sandbox_plan_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print plan without executing (default: True)",
    )
    agents_sandbox_plan_p.set_defaults(func=agents.sandbox_plan)

    # --- local-model ---
    local_model_p = sub.add_parser("local-model", help="Local Model Door helpers")
    local_model_sub = local_model_p.add_subparsers(
        dest="local_model_command", metavar="<subcommand>"
    )
    local_model_sub.required = True

    local_model_doctor_p = local_model_sub.add_parser(
        "doctor", help="Inspect local model runtime availability without pulling or inference"
    )
    local_model_doctor_p.set_defaults(func=local_model.doctor)

    local_model_profiles_p = local_model_sub.add_parser(
        "profiles", help="List built-in local model profile references"
    )
    local_model_profiles_p.set_defaults(func=local_model.profiles)

    local_model_plan_p = local_model_sub.add_parser(
        "plan", help="Render a local model runtime plan without pulling weights"
    )
    local_model_plan_p.add_argument(
        "--profile",
        default="local-llama32-1b",
        choices=sorted(local_model.LOCAL_MODEL_PROFILES),
        help="Local model profile key",
    )
    local_model_plan_p.set_defaults(func=local_model.plan)

    local_model_route_p = local_model_sub.add_parser(
        "route", help="Render a hash-only local model route decision"
    )
    local_model_route_p.add_argument(
        "--task-class",
        required=True,
        choices=[
            "router",
            "triage",
            "summarization",
            "rewrite",
            "office-assist",
            "agent-machine-assist",
            "offline-fallback",
            "coding-assist",
            "privacy-first-chat",
            "complex-reasoning",
        ],
        help="Task class to route",
    )
    local_model_route_p.add_argument(
        "--prompt",
        default=None,
        help="Optional prompt text; only a SHA-256 hash is emitted",
    )
    local_model_route_p.add_argument(
        "--personalization-ref",
        default=None,
        help="Optional personal model/adaptation governance reference",
    )
    local_model_route_p.add_argument(
        "--router-binding-ref",
        default=local_model.DEFAULT_ROUTER_BINDING_REF,
        help="Model-router binding reference",
    )
    local_model_route_p.set_defaults(func=local_model.route)

    local_model_evidence_p = local_model_sub.add_parser(
        "evidence", help="Local model evidence helpers"
    )
    local_model_evidence_sub = local_model_evidence_p.add_subparsers(
        dest="local_model_evidence_command", metavar="<subcommand>"
    )
    local_model_evidence_sub.required = True
    local_model_evidence_inspect_p = local_model_evidence_sub.add_parser(
        "inspect", help="Inspect local model route evidence JSON"
    )
    local_model_evidence_inspect_p.add_argument("path", help="Path to local model evidence JSON")
    local_model_evidence_inspect_p.set_defaults(func=local_model.evidence_inspect)

    # --- agent-machine ---
    agent_machine_p = sub.add_parser("agent-machine", help="Agent Machine helpers")
    agent_machine_sub = agent_machine_p.add_subparsers(
        dest="agent_machine_command", metavar="<subcommand>"
    )
    agent_machine_sub.required = True

    mounts_p = agent_machine_sub.add_parser("mounts", help="Agent Machine mount helpers")
    mounts_sub = mounts_p.add_subparsers(dest="agent_machine_mounts_command", metavar="<subcommand>")
    mounts_sub.required = True

    def add_mount_common(p):
        p.add_argument("--profile", default="macos-podman", help="Agent Machine profile name")
        p.add_argument("--dev-root", default="~/dev", help="Host code/repository root")
        p.add_argument(
            "--docs-root",
            default="~/Documents/SourceOS/agent-output",
            help="Host generated document/report output root",
        )
        p.add_argument(
            "--downloads-root",
            default="~/Downloads/SourceOS/agent-downloads",
            help="Host scoped browser downloads root",
        )

    mounts_plan_p = mounts_sub.add_parser("plan", help="Render mount plan (dry-run)")
    add_mount_common(mounts_plan_p)
    mounts_plan_p.set_defaults(func=agent_machine.mounts_plan)

    mounts_init_p = mounts_sub.add_parser(
        "init", help="Render or execute guarded local directory materialization"
    )
    add_mount_common(mounts_init_p)
    mounts_init_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print plan without creating directories or mounts (default: True)",
    )
    mounts_init_p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Create only explicitly-scoped output/download directories; does not create Podman mounts",
    )
    mounts_init_p.add_argument(
        "--policy-ok",
        action="store_true",
        default=False,
        help="Confirm Policy Fabric/operator approval for guarded local materialization",
    )
    mounts_init_p.add_argument(
        "--evidence-out",
        default=None,
        help="Optional path to write AgentMachineMountEvidence JSON",
    )
    mounts_init_p.set_defaults(func=agent_machine.mounts_init)

    mounts_inspect_p = mounts_sub.add_parser("inspect", help="Inspect default/local mount posture")
    add_mount_common(mounts_inspect_p)
    mounts_inspect_p.add_argument(
        "--include-downloads",
        action="store_true",
        default=False,
        help="Include scoped browser downloads mount in output",
    )
    mounts_inspect_p.set_defaults(func=agent_machine.mounts_inspect)

    mounts_evidence_p = mounts_sub.add_parser("evidence", help="Mount evidence helpers")
    mounts_evidence_sub = mounts_evidence_p.add_subparsers(
        dest="agent_machine_mounts_evidence_command", metavar="<subcommand>"
    )
    mounts_evidence_sub.required = True
    mounts_evidence_inspect_p = mounts_evidence_sub.add_parser(
        "inspect", help="Inspect an Agent Machine mount evidence JSON file"
    )
    mounts_evidence_inspect_p.add_argument("path", help="Path to mount evidence JSON file")
    mounts_evidence_inspect_p.set_defaults(func=agent_machine.mounts_evidence_inspect)

    # --- office ---
    office_p = sub.add_parser("office", help="Office Plane helpers")
    office_sub = office_p.add_subparsers(dest="office_command", metavar="<subcommand>")
    office_sub.required = True

    def add_office_common(p):
        p.add_argument("--workroom-id", default="workroom-local-default", help="Professional Workroom id")
        p.add_argument("--title", default="Untitled Office Artifact", help="Office artifact title")
        p.add_argument(
            "--artifact-type",
            default="document",
            choices=office.SUPPORTED_ARTIFACT_TYPES,
            help="Office artifact type",
        )
        p.add_argument(
            "--format",
            default="docx",
            choices=office.SUPPORTED_FORMATS,
            help="Office artifact output format",
        )
        p.add_argument("--backend", default="libreoffice", help="Office backend engine")
        p.add_argument("--mode", default="local-headless", help="Office backend mode")
        p.add_argument(
            "--output-root",
            default="~/Documents/SourceOS/agent-output",
            help="Host Office output root",
        )
        p.add_argument(
            "--downloads-root",
            default="~/Downloads/SourceOS/agent-downloads",
            help="Host scoped browser downloads root",
        )
        p.add_argument("--template-root", default="~/dev", help="Host template/code root")

    office_doctor_p = office_sub.add_parser("doctor", help="Inspect local Office backend availability")
    office_doctor_p.set_defaults(func=office.doctor)

    office_plan_p = office_sub.add_parser("plan", help="Render OfficeArtifact-compatible plan")
    add_office_common(office_plan_p)
    office_plan_p.set_defaults(func=office.plan)

    office_generate_p = office_sub.add_parser(
        "generate", help="Render or execute guarded Office text/Markdown/JSON generation"
    )
    add_office_common(office_generate_p)
    office_generate_p.add_argument("--template", default=None, help="Optional template reference")
    office_generate_p.add_argument("--prompt-ref", default=None, help="Optional prompt/context reference")
    office_generate_p.add_argument("--data-ref", default=None, help="Optional structured data reference")
    office_generate_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print generation plan without writing files (default: True)",
    )
    office_generate_p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Write txt/md/json artifacts only; Office binary generation remains disabled",
    )
    office_generate_p.add_argument(
        "--policy-ok",
        action="store_true",
        default=False,
        help="Confirm Policy Fabric/operator approval for guarded Office generation",
    )
    office_generate_p.add_argument(
        "--evidence-out",
        default=None,
        help="Optional path to write OfficeArtifactEvidence JSON",
    )
    office_generate_p.set_defaults(func=office.generate)

    office_convert_p = office_sub.add_parser(
        "convert", help="Render or execute guarded LibreOffice conversion"
    )
    office_convert_p.add_argument("input", help="Input Office artifact path")
    office_convert_p.add_argument("--to", required=True, help="Target format, e.g. pdf, docx, pptx")
    add_office_common(office_convert_p)
    office_convert_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print conversion plan without writing files (default: True)",
    )
    office_convert_p.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Run LibreOffice conversion under guarded local execution",
    )
    office_convert_p.add_argument(
        "--policy-ok",
        action="store_true",
        default=False,
        help="Confirm Policy Fabric/operator approval for guarded Office conversion",
    )
    office_convert_p.add_argument(
        "--evidence-out",
        default=None,
        help="Optional path to write OfficeArtifactEvidence JSON",
    )
    office_convert_p.set_defaults(func=office.convert)

    office_inspect_p = office_sub.add_parser("inspect", help="Inspect an Office artifact file")
    office_inspect_p.add_argument("path", help="Path to Office artifact file")
    office_inspect_p.set_defaults(func=office.inspect)

    office_evidence_p = office_sub.add_parser("evidence", help="Office evidence helpers")
    office_evidence_sub = office_evidence_p.add_subparsers(
        dest="office_evidence_command", metavar="<subcommand>"
    )
    office_evidence_sub.required = True
    office_evidence_inspect_p = office_evidence_sub.add_parser(
        "inspect", help="Inspect an Office Plane evidence JSON file"
    )
    office_evidence_inspect_p.add_argument("path", help="Path to Office evidence JSON file")
    office_evidence_inspect_p.set_defaults(func=office.evidence_inspect)

    return parser


def main(argv=None) -> int:
    """Main entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
