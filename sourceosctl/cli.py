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
    agent_machine,
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

    mounts_init_p = mounts_sub.add_parser("init", help="Render mount initialization plan (dry-run only)")
    add_mount_common(mounts_init_p)
    mounts_init_p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        dest="dry_run",
        help="Print plan without creating directories or mounts (default: True)",
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

    return parser


def main(argv=None) -> int:
    """Main entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
