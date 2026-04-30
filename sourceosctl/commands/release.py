"""release command: release artifact inspection."""

import json
import pathlib
import sys


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
