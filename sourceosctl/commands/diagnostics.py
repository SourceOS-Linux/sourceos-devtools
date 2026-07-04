"""Diagnostic redaction CLI helpers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REDACTION_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("cookies", re.compile(r"(?i)(\bcookie\s*[:=]\s*)([^\n]+)"), r"\1<redacted-cookie>"),
    ("bearer", re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9._~+/=-]+"), "Bearer <redacted-token>"),
    # Token-bearing identity fields (quoted JSON value or plain token blob).
    ("oauth", re.compile(r'(?is)("?(?:access_token|refresh_token|oauth_token|id_token)"?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|[^,\s]+)'), r'\1"<redacted-token>"'),
    ("api_keys", re.compile(r'(?is)("?(?:api[_-]?key|x-api-key|apikey|client_secret|authorization)"?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|[^,\s]+)'), r'\1"<redacted-secret>"'),
    ("secrets", re.compile(r'(?is)("?(?:secret|password|token)"?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|[^,\s]+)'), r'\1"<redacted-secret>"'),
    ("sensitive_ids", re.compile(r'(?is)("?(?:user|account|session|device|customer|tenant|workspace|organization|org|principal|subject)_id"?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|[^,\s]+)'), r'\1"<redacted-id>"'),
    # Prompt-bearing fields, including escaped multi-line quoted strings.
    (
        "model_prompts",
        re.compile(r'(?is)("?(?:prompt|model_prompt|system_prompt|user_prompt)"?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|[^,\n]+)'),
        r'\1"<redacted-prompt>"',
    ),
    ("policy_marked", re.compile(r"(?is)<policy-marked>.*?</policy-marked>"), "<policy-marked><redacted-policy-snippet></policy-marked>"),
]


def _redact(raw: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    redacted = raw
    for name, pattern, replacement in REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            counts[name] = count
    return redacted, counts


def redact_cmd(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(json.dumps({"type": "DiagnosticRedaction", "result": "fail", "errors": [f"missing input file: {input_path}"]}, indent=2, sort_keys=True))
        return 1
    raw = input_path.read_text(encoding="utf-8")
    redacted, counts = _redact(raw)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(redacted, encoding="utf-8")
        print(json.dumps({"type": "DiagnosticRedaction", "result": "pass", "input": str(input_path), "output": str(output_path), "redactionCounts": counts}, indent=2, sort_keys=True))
    else:
        print(redacted)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sourceosctl diagnostics", description="Diagnostic helpers")
    sub = parser.add_subparsers(dest="diagnostics_command", required=True)
    redact_p = sub.add_parser("redact", help="Redact sensitive tokens and snippets from diagnostic exports")
    redact_p.add_argument("input")
    redact_p.add_argument("--output", default=None)
    redact_p.set_defaults(func=redact_cmd)
    return parser


def diagnostics_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
