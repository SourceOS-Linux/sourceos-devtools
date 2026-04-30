"""agents command: agent sandbox helpers."""

import sys

_STUB_PLAN = [
    "1. Resolve agent identity from agent-registry (stub)",
    "2. Check tool-grant contracts (read-only, stub)",
    "3. Allocate isolated sandbox namespace (dry-run: would call nsjail or equivalent)",
    "4. Mount read-only source paths (dry-run: no mounts performed)",
    "5. Emit sandbox plan manifest to stdout",
]


def sandbox_plan(args) -> int:
    """Print an agent sandbox plan without executing it.

    Only --dry-run is supported; real execution is not implemented.
    """
    if not getattr(args, "dry_run", True):
        print(
            "error: only --dry-run is supported; sandbox execution is not implemented",
            file=sys.stderr,
        )
        return 1

    print("agents sandbox plan --dry-run")
    print("Planned steps (not executed):")
    for step in _STUB_PLAN:
        print(f"  {step}")
    print("\n(dry-run: no sandbox created)")
    return 0
