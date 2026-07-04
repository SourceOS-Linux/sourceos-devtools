#!/usr/bin/env python3
"""Scan repository files for unsafe local-agent persistence patterns.

This scanner encodes the lessons from the SourceOS local-agent incident. It is
intended for CI and local developer use. It scans text files for patterns that
should not appear in productized local-agent persistence without explicit review.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import sys
from collections.abc import Iterable


DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}

TEXT_SUFFIXES = {
    "",
    ".bash",
    ".conf",
    ".json",
    ".md",
    ".nix",
    ".plist",
    ".py",
    ".service",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclasses.dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    pattern: re.Pattern[str]
    message: str


@dataclasses.dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int
    message: str
    excerpt: str


RULES = [
    Rule(
        id="launchd-root-user-agent",
        severity="high",
        pattern=re.compile(r"/Library/LaunchAgents/[^\s'\"]+", re.IGNORECASE),
        message="system-wide LaunchAgents are unsafe for user-session agents; prefer ~/Library/LaunchAgents or an explicit system daemon",
    ),
    Rule(
        id="launchd-keepalive-true",
        severity="high",
        pattern=re.compile(r"<key>KeepAlive</key>\s*<true/>|KeepAlive\s*=\s*true|\"KeepAlive\"\s*[:=]>?\s*true", re.IGNORECASE),
        message="KeepAlive=true requires bounded restart policy and health checks",
    ),
    Rule(
        id="tmp-product-log",
        severity="medium",
        pattern=re.compile(r"/tmp/[^\s'\"]*\.log", re.IGNORECASE),
        message="product local-agent logs must not use /tmp as primary storage",
    ),
    Rule(
        id="ambient-gcloud-helper",
        severity="high",
        pattern=re.compile(r"gcloud\.auth\.docker-helper|\"gcloud\"|credHelpers", re.IGNORECASE),
        message="noninteractive local-agent runtime must not depend on ambient gcloud/Docker credential helpers",
    ),
    Rule(
        id="direct-google-artifact-runtime",
        severity="high",
        pattern=re.compile(r"us-central1-docker\.pkg\.dev/[^\s'\"]+", re.IGNORECASE),
        message="persistent runtime should use local image tags and explicit auth mode; preserve remote image only as provenance",
    ),
    Rule(
        id="raw-podman-run-persistence",
        severity="medium",
        pattern=re.compile(r"podman\s+[^\n]*run\s+[^\n]*(--rm|--replace|--name)", re.IGNORECASE),
        message="persistent podman run commands must go through sourceos-agent preflight/wrapper contract",
    ),
    Rule(
        id="raw-shell-launch-wrapper",
        severity="medium",
        pattern=re.compile(r"/bin/sh\s+-c|/bin/bash\s+-c", re.IGNORECASE),
        message="raw shell command persistence should be generated/linted by SourceOS tooling",
    ),
    Rule(
        id="opaque-nix-store-target",
        severity="medium",
        pattern=re.compile(r"/nix/store/[a-z0-9]{20,}[^\s'\"]*", re.IGNORECASE),
        message="Nix store paths should not be the only operator-facing service target; use stable wrappers/status tooling",
    ),
]


def iter_files(root: pathlib.Path, include_docs: bool) -> Iterable[pathlib.Path]:
    for path in root.rglob("*"):
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        if not path.is_file():
            continue
        if not include_docs and path.suffix.lower() == ".md":
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def scan_file(path: pathlib.Path, root: pathlib.Path) -> list[Finding]:
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return []
    findings: list[Finding] = []
    rel = str(path.relative_to(root))
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            if rule.pattern.search(line):
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        path=rel,
                        line=lineno,
                        message=rule.message,
                        excerpt=line.strip()[:240],
                    )
                )
    return findings


def scan(root: pathlib.Path, include_docs: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root, include_docs=include_docs):
        findings.extend(scan_file(path, root))
    return findings


def print_text(findings: list[Finding]) -> None:
    if not findings:
        print("local persistence scan: no unsafe patterns found")
        return
    print(f"local persistence scan: {len(findings)} finding(s)")
    for finding in findings:
        print(
            f"[{finding.severity}] {finding.rule_id} {finding.path}:{finding.line}\n"
            f"  {finding.message}\n"
            f"  excerpt: {finding.excerpt}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for unsafe SourceOS local-agent persistence patterns")
    parser.add_argument("root", nargs="?", default=".", help="Repository root to scan")
    parser.add_argument("--include-docs", action="store_true", default=False, help="Also scan Markdown documentation")
    parser.add_argument("--json", action="store_true", default=False, help="Emit JSON findings")
    parser.add_argument("--fail-on", choices=["none", "medium", "high"], default="high", help="Failure threshold")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    findings = scan(root, include_docs=args.include_docs)

    if args.json:
        import json

        print(json.dumps([dataclasses.asdict(f) for f in findings], indent=2, sort_keys=True))
    else:
        print_text(findings)

    if args.fail_on == "none":
        return 0
    severities = {"medium": {"medium", "high"}, "high": {"high"}}[args.fail_on]
    return 1 if any(f.severity in severities for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
