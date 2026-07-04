#!/usr/bin/env python3
"""Validate sourceos-devtools packaging scaffolding."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "packaging/homebrew/Formula/sourceos-devtools.rb"
INSTALL_DOC = ROOT / "docs/install.md"

REQUIRED_FORMULA_SNIPPETS = [
    "class SourceosDevtools < Formula",
    "SourceOS developer and Portable AI Kit operator tools",
    "sourceosctl",
    "sourceos-portable-ai",
    "PortableAIProfiles",
]

FORBIDDEN_FORMULA_SNIPPETS = [
    "ollama pull",
    "ollama run",
    "ollama serve",
    "HUGGINGFACE",
    "HF_TOKEN",
    "OPENAI_API_KEY",
]

REQUIRED_DOC_SNIPPETS = [
    "sourceosctl portable-ai profiles",
    "portable-ai preflight",
    "portable-ai prepare",
    "portable-ai start-plan",
    "portable-ai stop-plan",
    "portable-ai byom verify",
    "prompt egress is denied",
]


def fail(message: str) -> int:
    print(f"ERR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not FORMULA.exists():
        return fail(f"missing {FORMULA.relative_to(ROOT)}")
    if not INSTALL_DOC.exists():
        return fail(f"missing {INSTALL_DOC.relative_to(ROOT)}")

    formula = FORMULA.read_text(encoding="utf-8")
    install_doc = INSTALL_DOC.read_text(encoding="utf-8")

    for snippet in REQUIRED_FORMULA_SNIPPETS:
        if snippet not in formula:
            return fail(f"formula missing required snippet: {snippet}")
    for snippet in FORBIDDEN_FORMULA_SNIPPETS:
        if snippet in formula:
            return fail(f"formula contains forbidden side-effect/secrets snippet: {snippet}")
    for snippet in REQUIRED_DOC_SNIPPETS:
        if snippet not in install_doc:
            return fail(f"install doc missing required snippet: {snippet}")

    print("Packaging validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
