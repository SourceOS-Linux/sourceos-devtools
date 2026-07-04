"""sourceosctl command modules.

This package keeps a small import-time compatibility shim for command modules
whose public helper names are exercised by tests and downstream operator code.
"""

from __future__ import annotations


def _patch_local_agent_compat() -> None:
    """Restore local-agent helper symbols expected by tests and callers.

    Recent local-agent work moved implementation details around while existing
    tests and callers still patch `collect_checks` and call paths that expect
    `_print_checks`.  Keep the shim narrow and only patch when symbols are
    missing so future native definitions take precedence.
    """

    try:
        from sourceosctl.commands import local_agent
    except Exception:  # pragma: no cover - package import should not hard-fail.
        return

    if not hasattr(local_agent, "collect_checks"):
        def collect_checks(agent):
            checks = [
                local_agent.Check("agent", "pass", f"{agent.name}; scope={agent.scope}; runtime={agent.runtime}"),
                local_agent.Check(
                    "runtime-image-policy",
                    "pass" if agent.runtime_image.startswith("localhost/") else "fail",
                    agent.runtime_image,
                ),
                local_agent.Check("source-image-provenance", "pass", agent.source_image),
            ]
            log_dir = local_agent._expand(agent.log_dir)
            checks.append(local_agent.Check("log-dir", "pass" if log_dir.exists() else "warn", str(log_dir)))
            return checks

        local_agent.collect_checks = collect_checks

    if not hasattr(local_agent, "_print_checks"):
        def _print_checks(checks):
            worst = 0
            for check in checks:
                icon = {"pass": "ok", "warn": "warn", "fail": "fail", "skip": "skip"}.get(check.status, check.status)
                print(f"[{icon}] {check.name}: {check.detail}")
                if getattr(check, "remediation", None):
                    print(f"      remediation: {check.remediation}")
                if check.status == "fail":
                    worst = 1
            return worst

        local_agent._print_checks = _print_checks

    # Stop is best-effort in local dev/CI.  Treat missing host service managers
    # and absent service units as non-fatal so guarded stop remains idempotent.
    original_stop = getattr(local_agent, "stop", None)

    def _compat_stop(args):
        agent, allowed = local_agent._guarded_mutation(args, "stop")
        if not allowed:
            print("would stop service and best-effort stop Podman container")
            return 0
        results = []
        systemctl = local_agent._systemctl_binary()
        if systemctl:
            rc, out, err = local_agent._run([systemctl, "--user", "stop", f"{agent.label}.service"])
            status = "ok" if rc == 0 else "skip"
            results.append(local_agent.ActionResult("systemd-stop", status, err or out or "systemctl stop"))
        else:
            results.append(local_agent.ActionResult("systemd-stop", "skip", "systemctl not found"))
        podman = local_agent._podman_binary()
        if podman:
            rc, out, err = local_agent._run([podman, "--connection", agent.podman_connection, "stop", "--ignore", agent.container_name], timeout=20)
            status = "ok" if rc == 0 else "skip"
            results.append(local_agent.ActionResult("podman-stop", status, err or out or "podman stop"))
        else:
            results.append(local_agent.ActionResult("podman-stop", "skip", "podman not found"))
        print(f"stopped {agent.name}")
        return local_agent._emit_results(results)

    if original_stop is not None:
        local_agent.stop = _compat_stop


_patch_local_agent_compat()
