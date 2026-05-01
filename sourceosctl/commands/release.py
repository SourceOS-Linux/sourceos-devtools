"""release command: release artifact inspection."""

import json
import pathlib
import sys

# Files that must be present in a valid NLBoot release archive directory.
_NLBOOT_REQUIRED_FILES = [
    "nlboot-client",
    "Cargo.lock",
    "cargo-metadata.json",
    "sbom.spdx.json",
    "release-manifest.json",
]


def inspect_archive(args) -> int:
    """Inspect a NLBoot release archive directory for required files. Read-only."""
    path = pathlib.Path(args.path)
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1
    if not path.is_dir():
        print(f"error: not a directory: {path}", file=sys.stderr)
        return 1

    print(f"NLBoot release archive: {path}")
    missing = []
    for name in _NLBOOT_REQUIRED_FILES:
        entry = path / name
        if entry.exists():
            print(f"  ok  {name}")
        else:
            print(f"  MISSING  {name}")
            missing.append(name)

    if missing:
        print(
            f"error: {len(missing)} required file(s) missing: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    print("ok: all required NLBoot release files present")
    return 0


def inspect(args) -> int:
    """Inspect a release artifact. Read-only."""
    path = pathlib.Path(args.path)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1

    schema = data.get("schemaVersion", "<unknown>")
    name = data.get("name", "<unknown>")
    version = data.get("version", "<unknown>")
    print(f"Release artifact: {path}")
    print(f"  schemaVersion : {schema}")
    print(f"  name          : {name}")
    print(f"  version       : {version}")

    for key, value in data.items():
        if key in ("schemaVersion", "name", "version"):
            continue
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        elif isinstance(value, list):
            print(f"  {key}: {', '.join(str(v) for v in value)}")
        else:
            print(f"  {key}: {value}")

    return 0
