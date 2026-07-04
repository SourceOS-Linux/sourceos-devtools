"""Validation script for sourceos-devtools repository scaffold."""

import pathlib
import sys

REQUIRED = [
    "README.md",
    "AGENTS.md",
    ".github/copilot-instructions.md",
    "docs/DEVTOOLS_SCOPE.md",
    "repo.maturity.yaml",
]

for path in REQUIRED:
    p = pathlib.Path(path)
    if not p.exists():
        raise SystemExit(f"MISSING: {path}")
    if not p.read_text().strip():
        raise SystemExit(f"EMPTY: {path}")

print("OK: sourceos-devtools validation")
