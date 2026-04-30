"""doctor command: run environment health checks."""

import platform
import shutil
import sys


def run(args) -> int:
    """Print a summary of environment health. Read-only."""
    checks = []

    checks.append(("python", sys.version.split()[0], True))
    checks.append(("platform", platform.system(), True))

    git_path = shutil.which("git")
    checks.append(("git", git_path if git_path else "not found", git_path is not None))

    nix_path = shutil.which("nix")
    checks.append(("nix", nix_path if nix_path else "not found", False))

    all_ok = True
    for name, value, required in checks:
        status = "ok" if value and value != "not found" else ("warn" if not required else "FAIL")
        if status == "FAIL":
            all_ok = False
        print(f"  {status:<6} {name}: {value}")

    if all_ok:
        print("\ndoctor: all required checks passed")
    else:
        print("\ndoctor: one or more required checks failed", file=sys.stderr)
        return 1

    return 0
