"""fingerprint command: environment fingerprint utilities."""

import platform
import shutil
import sys


_FIELDS = [
    ("os", lambda: platform.system()),
    ("os_version", lambda: platform.version()),
    ("machine", lambda: platform.machine()),
    ("python", lambda: sys.version.split()[0]),
    ("git", lambda: shutil.which("git") or "not found"),
    ("nix", lambda: shutil.which("nix") or "not found"),
]


def collect(args) -> int:
    """Collect environment fingerprint.

    With --dry-run (default and only mode) prints what would be collected
    without writing anything to disk.
    """
    if not getattr(args, "dry_run", True):
        print(
            "error: only --dry-run is supported; mutating collect is not implemented",
            file=sys.stderr,
        )
        return 1

    print("fingerprint collect --dry-run")
    print("Fields that would be collected:")
    for name, getter in _FIELDS:
        print(f"  {name}: {getter()}")
    print("\n(dry-run: no data written)")
    return 0
