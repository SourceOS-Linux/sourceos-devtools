"""nlboot command: NLBoot evidence inspection helpers."""

import json
import pathlib
import sys


def inspect_evidence(args) -> int:
    """Inspect a NLBoot evidence file. Read-only."""
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
    kind = data.get("kind", "<unknown>")
    print(f"NLBoot evidence: {path}")
    print(f"  schemaVersion : {schema}")
    print(f"  kind          : {kind}")

    for key, value in data.items():
        if key in ("schemaVersion", "kind"):
            continue
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    return 0
