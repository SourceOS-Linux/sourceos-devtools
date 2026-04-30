"""nlboot command: NLBoot evidence inspection helpers."""

import json
import pathlib
import sys

# Repo-local schema directory (no network fetches).
_SCHEMA_DIR = pathlib.Path(__file__).parent.parent.parent / "fixtures" / "schemas"

_KNOWN_SCHEMAS = {
    "nlboot-evidence.v1": _SCHEMA_DIR / "nlboot-evidence.v1.schema.json",
}


def _load_schema(schema_version: str):
    """Load a vendored JSON Schema by schemaVersion string.

    Returns the parsed schema dict or raises FileNotFoundError / ValueError.
    """
    schema_path = _KNOWN_SCHEMAS.get(schema_version)
    if schema_path is None:
        raise ValueError(f"no bundled schema for schemaVersion '{schema_version}'")
    return json.loads(schema_path.read_text())


def validate_evidence(args) -> int:
    """Validate a NLBoot evidence file against its bundled schema. Read-only."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        print(
            "error: jsonschema package is required for validation "
            "(pip install jsonschema)",
            file=sys.stderr,
        )
        return 1

    path = pathlib.Path(args.path)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1

    schema_version = data.get("schemaVersion", "")
    try:
        schema = _load_schema(schema_version)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: cannot load schema: {exc}", file=sys.stderr)
        return 1

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        print(f"ok: {path} is valid ({schema_version})")
        return 0

    print(f"error: {path} failed schema validation ({schema_version}):", file=sys.stderr)
    for err in errors:
        field = ".".join(str(p) for p in err.absolute_path) or "<root>"
        print(f"  {field}: {err.message}", file=sys.stderr)
    return 1


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

    if getattr(args, "validate", False):
        return validate_evidence(args)

    return 0
