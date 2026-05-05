"""SourceOS local-agent runtime helpers.

This module is intentionally conservative: status, preflight, doctor, and logs are
read-only. Mutating verbs require both --execute and --policy-ok. The goal is to
prevent the class of failure where a Nix-generated local service silently becomes
opaque, unbounded persistence.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import platform
import plistlib
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class LocalAgent:
    """Static declaration for a known local agent."""

    name: str
    label: str
    scope: str
    runtime: str
    container_name: str
    runtime_image: str
    source_image: str
    podman_connection: str
    authfile: str
    user_plist: str
    legacy_system_plist: str
    log_dir: str
    app_log: str


DEFAULT_AGENTS: dict[str, LocalAgent] = {
    "node-commander": LocalAgent(
        name="node-commander",
        label="org.socioprophet.node-commander",
        scope="user",
        runtime="podman",
        container_name="node-commander",
        runtime_image="localhost/socioprophet/node-commander:dev-boot",
        source_image=(
            "us-central1-docker.pkg.dev/socioprophet-web/"
            "node-commander/node-commander:dev-boot"
        ),
        podman_connection="podman-machine-default",
        authfile="~/.config/containers/empty-auth.json",
        user_plist="~/Library/LaunchAgents/org.socioprophet.node-commander.plist",
        legacy_system_plist="/Library/LaunchAgents/org.socioprophet.node-commander.plist",
        log_dir="~/Library/Logs/SocioProphet",
        app_log="~/Library/Logs/SocioProphet/node-commander.log",
    )
}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    remediation: Optional[str] = None


@dataclass
class ActionResult:
    action: str
    status: str
    detail: str
    path: Optional[str] = None


def _expand(path: str) -> pathlib.Path:
    return pathlib.Path(os.path.expandvars(os.path.expanduser(path)))


def _run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"missing executable: {cmd[0]}"
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timed out"


def _podman_binary() -> Optional[str]:
    for candidate in ("/opt/homebrew/bin/podman", shutil.which("podman")):
        if candidate and pathlib.Path(candidate).exists():
            return candidate
    return None


def _launchctl_binary() -> Optional[str]:
    for candidate in ("/bin/launchctl", shutil.which("launchctl")):
        if candidate and pathlib.Path(candidate).exists():
            return candidate
    return None


def _systemctl_binary() -> Optional[str]:
    return shutil.which("systemctl")


def _timestamp() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def _iso_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _authfile_is_empty_auth(path: pathlib.Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "authfile missing"
    try:
        payload = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001 - diagnostic surface should not crash.
        return False, f"authfile is not valid JSON: {exc}"
    if payload == {"auths": {}}:
        return True, "empty authfile present"
    return False, "authfile is not empty-authfile mode"


def _redacted_json(path: pathlib.Path) -> str:
    if not path.exists():
        return "missing"
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return "present but not valid JSON"

    def redact(value):
        if isinstance(value, dict):
            return {
                k: ("<redacted>" if k.lower() in {"auth", "identitytoken", "password", "token"} else redact(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [redact(v) for v in value]
        return value

    return json.dumps(redact(payload), indent=2, sort_keys=True)


def _agent_or_error(name: str) -> LocalAgent:
    try:
        return DEFAULT_AGENTS[name]
    except KeyError as exc:
        known = ", ".join(sorted(DEFAULT_AGENTS))
        raise SystemExit(f"unknown local agent: {name}; known agents: {known}") from exc


def _launcher_path(agent: LocalAgent) -> pathlib.Path:
    return _expand(f"~/.local/bin/sourceos-agents/{agent.name}-launch")


def _systemd_user_unit_path(agent: LocalAgent) -> pathlib.Path:
    return _expand(f"~/.config/systemd/user/{agent.label}.service")


def _render_launcher(agent: LocalAgent) -> str:
    podman = _podman_binary() or "/opt/homebrew/bin/podman"
    auth = str(_expand(agent.authfile))
    log = str(_expand(agent.app_log))
    return f'''#!/usr/bin/env bash
set -euo pipefail

PODMAN="{podman}"
CONN="{agent.podman_connection}"
IMAGE="{agent.runtime_image}"
AUTH="{auth}"
LOG="{log}"
NAME="{agent.container_name}"

ts() {{
  /bin/date "+%Y-%m-%dT%H:%M:%S%z" 2>/dev/null || date "+%Y-%m-%dT%H:%M:%S%z"
}}

mkdir -p "$(dirname "$AUTH")" "$(dirname "$LOG")"
[ -f "$AUTH" ] || printf '{{"auths":{{}}}}\n' > "$AUTH"

{{
  echo "[$(ts)] {agent.name} launch requested"

  if ! "$PODMAN" --connection "$CONN" info >/dev/null 2>&1; then
    echo "[$(ts)] Podman machine/socket unavailable; exiting cleanly."
    exit 0
  fi

  if ! "$PODMAN" --connection "$CONN" image exists "$IMAGE"; then
    echo "[$(ts)] Local image missing: $IMAGE"
    exit 0
  fi

  echo "[$(ts)] starting container: $IMAGE"
  exec "$PODMAN" --connection "$CONN" run --pull=never --authfile "$AUTH" --rm --replace \
    --name "$NAME" \
    "$IMAGE"
}} >> "$LOG" 2>&1
'''


def _render_launchd_plist(agent: LocalAgent, launcher_path: pathlib.Path) -> bytes:
    log_dir = _expand(agent.log_dir)
    payload = {
        "Label": agent.label,
        "ProgramArguments": [str(launcher_path)],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(log_dir / f"{agent.name}.launchd.out.log"),
        "StandardErrorPath": str(log_dir / f"{agent.name}.launchd.err.log"),
    }
    return plistlib.dumps(payload, sort_keys=True)


def _render_systemd_user_unit(agent: LocalAgent, launcher_path: pathlib.Path) -> str:
    return f"""[Unit]
Description=SourceOS local agent: {agent.name}
Documentation=https://github.com/SourceOS-Linux/sourceos-spec
After=default.target

[Service]
Type=simple
ExecStart={launcher_path}
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=3600
StartLimitBurst=3

[Install]
WantedBy=default.target
"""


def _write_text(path: pathlib.Path, content: str) -> ActionResult:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return ActionResult("write", "ok", f"wrote {path}", str(path))
    except Exception as exc:  # noqa: BLE001
        return ActionResult("write", "warn", f"could not write {path}: {exc}", str(path))


def _write_bytes(path: pathlib.Path, content: bytes) -> ActionResult:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return ActionResult("write", "ok", f"wrote {path}", str(path))
    except Exception as exc:  # noqa: BLE001
        return ActionResult("write", "warn", f"could not write {path}: {exc}", str(path))


def _chmod(path: pathlib.Path, mode: int, label: str) -> ActionResult:
    try:
        path.chmod(mode)
        return ActionResult(label, "ok", f"chmod {oct(mode)} {path}", str(path))
    except Exception as exc:  # noqa: BLE001
        return ActionResult(label, "warn", f"could not chmod {path}: {exc}", str(path))


def _copy_if_exists(src: pathlib.Path, dst: pathlib.Path, label: str) -> ActionResult:
    if not src.exists():
        return ActionResult(label, "skip", f"missing: {src}", str(src))
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return ActionResult(label, "ok", f"copied {src} -> {dst}", str(dst))
    except Exception as exc:  # noqa: BLE001
        return ActionResult(label, "warn", f"could not copy {src}: {exc}", str(src))


def _move_if_exists(src: pathlib.Path, dst: pathlib.Path, label: str) -> ActionResult:
    if not src.exists():
        return ActionResult(label, "skip", f"missing: {src}", str(src))
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return ActionResult(label, "ok", f"moved {src} -> {dst}", str(dst))
    except Exception as exc:  # noqa: BLE001
        return ActionResult(label, "warn", f"could not move {src}: {exc}", str(src))


def _run_capture(cmd: list[str], out_path: pathlib.Path, action: str, timeout: int = 12) -> ActionResult:
    rc, out, err = _run(cmd, timeout=timeout)
    payload = {
        "command": cmd,
        "returncode": rc,
        "stdout": out,
        "stderr": err,
        "capturedAt": _iso_now(),
    }
    result = _write_text(out_path, json.dumps(payload, indent=2, sort_keys=True))
    if rc == 0:
        return ActionResult(action, result.status, f"captured {' '.join(cmd)}", str(out_path))
    return ActionResult(action, "warn", f"command returned {rc}: {' '.join(cmd)}", str(out_path))


def _runtime_blocking_failures(agent: LocalAgent) -> list[Check]:
    blocking = {
        "runtime-image-policy",
        "podman",
        "podman-socket",
        "runtime-image",
        "runtime-authfile",
    }
    return [c for c in collect_checks(agent) if c.name in blocking and c.status == "fail"]


def _emit_results(results: list[ActionResult]) -> int:
    worst = 0
    for result in results:
        print(f"[{result.status}] {result.action}: {result.detail}")
        if result.status == "warn":
            worst = 1
    return worst


def _stage_agent(agent: LocalAgent, output_dir: pathlib.Path) -> tuple[pathlib.Path, list[ActionResult]]:
    stage_dir = output_dir / f"{agent.name}-{_timestamp()}"
    launcher = stage_dir / "bin" / f"{agent.name}-launch"
    plist = stage_dir / "launchd" / f"{agent.label}.plist"
    unit = stage_dir / "systemd-user" / f"{agent.label}.service"
    results = [
        _write_text(launcher, _render_launcher(agent)),
        _chmod(launcher, 0o755, "chmod-launcher"),
        _write_bytes(plist, _render_launchd_plist(agent, launcher)),
        _write_text(unit, _render_systemd_user_unit(agent, launcher)),
        _write_text(stage_dir / "agent.json", json.dumps(asdict(agent), indent=2, sort_keys=True)),
    ]
    return stage_dir, results


def _install_agent(agent: LocalAgent) -> list[ActionResult]:
    results: list[ActionResult] = []
    launcher = _launcher_path(agent)
    auth = _expand(agent.authfile)
    log_dir = _expand(agent.log_dir)
    results.append(_write_text(auth, '{"auths":{}}\n'))
    results.append(_write_text(launcher, _render_launcher(agent)))
    results.append(_chmod(launcher, 0o755, "chmod-launcher"))
    results.append(_write_text(log_dir / ".sourceos-local-agent", f"managed-by=sourceos-agent\nagent={agent.name}\n"))

    if platform.system() == "Darwin":
        plist = _expand(agent.user_plist)
        results.append(_write_bytes(plist, _render_launchd_plist(agent, launcher)))
        results.append(_chmod(plist, 0o644, "chmod-plist"))
    else:
        unit = _systemd_user_unit_path(agent)
        results.append(_write_text(unit, _render_systemd_user_unit(agent, launcher)))
        results.append(_chmod(unit, 0o644, "chmod-systemd-unit"))
    results.append(_write_text(log_dir / f"{agent.name}.install-manifest.json", json.dumps({
        "agent": asdict(agent),
        "installedAt": _iso_now(),
        "launcher": str(launcher),
        "platform": platform.platform(),
    }, indent=2, sort_keys=True)))
    return results


def _capture_launchd(agent: LocalAgent, qdir: pathlib.Path) -> list[ActionResult]:
    results: list[ActionResult] = []
    if platform.system() != "Darwin":
        return [ActionResult("launchd", "skip", "not a Darwin host")]
    launchctl = _launchctl_binary()
    if not launchctl:
        return [ActionResult("launchd", "warn", "launchctl not found")]
    domain_label = f"gui/{os.getuid()}/{agent.label}"
    user_plist = _expand(agent.user_plist)
    results.append(_run_capture([launchctl, "print", domain_label], qdir / "launchd-print.json", "launchd-print"))
    results.append(_run_capture([launchctl, "print-disabled", f"gui/{os.getuid()}"], qdir / "launchd-disabled.json", "launchd-disabled"))
    results.append(_run_capture([launchctl, "bootout", f"gui/{os.getuid()}", str(user_plist)], qdir / "launchd-bootout.json", "launchd-bootout"))
    results.append(_run_capture([launchctl, "disable", domain_label], qdir / "launchd-disable.json", "launchd-disable"))
    return results


def _capture_podman(agent: LocalAgent, qdir: pathlib.Path) -> list[ActionResult]:
    podman = _podman_binary()
    if not podman:
        return [ActionResult("podman", "skip", "podman not found")]
    return [
        _run_capture([podman, "system", "connection", "list"], qdir / "podman-connections.json", "podman-connections"),
        _run_capture([podman, "machine", "list"], qdir / "podman-machines.json", "podman-machines"),
        _run_capture([podman, "--connection", agent.podman_connection, "info"], qdir / "podman-info.json", "podman-info"),
        _run_capture([podman, "--connection", agent.podman_connection, "ps", "-a", "--filter", f"name={agent.container_name}"], qdir / "podman-ps.json", "podman-ps"),
        _run_capture([podman, "--connection", agent.podman_connection, "image", "inspect", agent.runtime_image], qdir / "image-inspect.json", "image-inspect"),
        _run_capture([podman, "--connection", agent.podman_connection, "container", "inspect", agent.container_name], qdir / "container-inspect.json", "container-inspect"),
    ]


def _capture_redacted_auth(agent: LocalAgent, qdir: pathlib.Path) -> list[ActionResult]:
    targets = {
        "runtime-authfile-redacted.json": _expand(agent.authfile),
        "docker-config-redacted.json": _expand("~/.docker/config.json"),
        "containers-auth-redacted.json": _expand("~/.config/containers/auth.json"),
    }
    results = []
    for name, path in targets.items():
        results.append(_write_text(qdir / name, _redacted_json(path)))
    return results


def _quarantine_agent(agent: LocalAgent, output_dir: pathlib.Path) -> tuple[pathlib.Path, list[ActionResult]]:
    qdir = output_dir / f"{agent.name}-{_timestamp()}"
    qdir.mkdir(parents=True, exist_ok=False)
    results: list[ActionResult] = []

    checks = collect_checks(agent)
    results.append(_write_text(qdir / "checks.json", json.dumps([asdict(c) for c in checks], indent=2, sort_keys=True)))
    results.extend(_capture_launchd(agent, qdir))
    results.extend(_capture_podman(agent, qdir))
    results.extend(_capture_redacted_auth(agent, qdir))

    user_plist = _expand(agent.user_plist)
    legacy_plist = pathlib.Path(agent.legacy_system_plist)
    app_log = _expand(agent.app_log)
    log_dir = _expand(agent.log_dir)
    results.append(_copy_if_exists(app_log, qdir / app_log.name, "copy-app-log"))
    if log_dir.exists():
        for candidate in log_dir.glob(f"{agent.name}*.log"):
            results.append(_copy_if_exists(candidate, qdir / candidate.name, "copy-related-log"))

    results.append(_move_if_exists(user_plist, qdir / f"{user_plist.name}.disabled", "move-user-plist"))
    results.append(_move_if_exists(legacy_plist, qdir / f"{legacy_plist.name}.disabled", "move-legacy-system-plist"))

    manifest = {
        "agent": asdict(agent),
        "createdAt": _iso_now(),
        "platform": platform.platform(),
        "quarantineDir": str(qdir),
        "results": [asdict(r) for r in results],
        "operatorNotes": [
            "Review warning results; system-wide files may require sudo removal.",
            "Reinstall only through the SourceOS local-agent runtime contract.",
        ],
    }
    results.append(_write_text(qdir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True)))
    remediation = [
        f"# Quarantine remediation for {agent.name}",
        "",
        "1. Review `manifest.json` and warning results.",
        "2. Confirm no legacy system-wide plist remains.",
        "3. Confirm Podman container state is not stuck in `Stopping` or `Removing`.",
        "4. Reinstall only after `sourceos-agent preflight` passes.",
        "",
        "Useful commands:",
        "",
        f"```bash\nsourceos-agent preflight {agent.name}\nsourceos-agent status {agent.name}\n```",
    ]
    results.append(_write_text(qdir / "remediation.md", "\n".join(remediation) + "\n"))
    return qdir, results


def list_agents(_args: argparse.Namespace) -> int:
    for agent in DEFAULT_AGENTS.values():
        print(f"{agent.name}\t{agent.scope}\t{agent.runtime}\t{agent.runtime_image}")
    return 0


def preflight(args: argparse.Namespace) -> int:
    agent = _agent_or_error(args.agent)
    return _print_checks(collect_checks(agent))


def doctor(args: argparse.Namespace) -> int:
    agent = _agent_or_error(args.agent)
    print(f"SourceOS local-agent doctor: {agent.name}")
    return _print_checks(collect_checks(agent))


def status(args: argparse.Namespace) -> int:
    agent = _agent_or_error(args.agent)
    print(f"agent: {agent.name}")
    print(f"label: {agent.label}")
    print(f"scope: {agent.scope}")
    print(f"runtime: {agent.runtime}")
    print(f"runtime_image: {agent.runtime_image}")
    print(f"source_image: {agent.source_image}")
    print(f"authfile: {_expand(agent.authfile)}")
    print(f"user_plist: {_expand(agent.user_plist)}")
    print(f"legacy_system_plist: {agent.legacy_system_plist}")
    print(f"log_dir: {_expand(agent.log_dir)}")
    print()
    return _print_checks(collect_checks(agent))


def logs(args: argparse.Namespace) -> int:
    agent = _agent_or_error(args.agent)
    path = _expand(agent.app_log)
    if not path.exists():
        print(f"log missing: {path}", file=sys.stderr)
        return 1
    lines = args.lines
    data = path.read_text(errors="replace").splitlines()
    for line in data[-lines:]:
        print(line)
    return 0


def _guarded_mutation(args: argparse.Namespace, action: str) -> tuple[LocalAgent, bool]:
    agent = _agent_or_error(args.agent)
    if not (args.execute and args.policy_ok):
        print(f"planned {action}: {agent.name}")
        print("mutation not executed; pass --execute --policy-ok to allow guarded local changes")
        return agent, False
    return agent, True


def stage(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "stage")
    output = _expand(args.output_dir)
    if not allowed:
        print(f"would write generated launcher/plist/unit under: {output}")
        return 0
    stage_dir, results = _stage_agent(agent, output)
    print(f"staged {agent.name}: {stage_dir}")
    return _emit_results(results)


def install(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "install")
    if not allowed:
        print("would write launcher, authfile, logs marker, and user service definition")
        return 0
    failures = [c for c in _runtime_blocking_failures(agent) if c.name not in {"runtime-authfile"}]
    if failures and not args.force:
        print("install refused because runtime preflight has blocking failures:", file=sys.stderr)
        _print_checks(failures)
        print("pass --force to install staged service files without starting", file=sys.stderr)
        return 1
    results = _install_agent(agent)
    print(f"installed {agent.name}")
    return _emit_results(results)


def start(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "start")
    if not allowed:
        print("would enable/start user service after runtime preflight passes")
        return 0
    failures = _runtime_blocking_failures(agent)
    if failures:
        print("start refused because runtime preflight has blocking failures:", file=sys.stderr)
        _print_checks(failures)
        return 1
    results: list[ActionResult] = []
    if platform.system() == "Darwin":
        launchctl = _launchctl_binary()
        if not launchctl:
            results.append(ActionResult("start", "warn", "launchctl not found"))
        else:
            plist = _expand(agent.user_plist)
            domain = f"gui/{os.getuid()}"
            label = f"{domain}/{agent.label}"
            results.append(ActionResult("launchd-enable", "ok" if _run([launchctl, "enable", label])[0] == 0 else "warn", f"enable {label}"))
            rc, out, err = _run([launchctl, "bootstrap", domain, str(plist)])
            if rc not in {0, 37}:  # 37 can mean already bootstrapped on some macOS builds.
                results.append(ActionResult("launchd-bootstrap", "warn", err or out or f"bootstrap returned {rc}"))
            else:
                results.append(ActionResult("launchd-bootstrap", "ok", f"bootstrap {plist}"))
            rc, out, err = _run([launchctl, "kickstart", "-k", label])
            results.append(ActionResult("launchd-kickstart", "ok" if rc == 0 else "warn", err or out or f"kickstart returned {rc}"))
    else:
        systemctl = _systemctl_binary()
        if not systemctl:
            results.append(ActionResult("start", "warn", "systemctl not found"))
        else:
            unit = f"{agent.label}.service"
            for cmd, action in [
                ([systemctl, "--user", "daemon-reload"], "systemd-daemon-reload"),
                ([systemctl, "--user", "enable", unit], "systemd-enable"),
                ([systemctl, "--user", "start", unit], "systemd-start"),
            ]:
                rc, out, err = _run(cmd)
                results.append(ActionResult(action, "ok" if rc == 0 else "warn", err or out or " ".join(cmd)))
    print(f"started {agent.name}")
    return _emit_results(results)


def stop(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "stop")
    if not allowed:
        print("would stop service and best-effort stop Podman container")
        return 0
    results: list[ActionResult] = []
    if platform.system() == "Darwin":
        launchctl = _launchctl_binary()
        if launchctl:
            results.append(_run_capture([launchctl, "bootout", f"gui/{os.getuid()}", str(_expand(agent.user_plist))], _expand(agent.log_dir) / f"{agent.name}.last-bootout.json", "launchd-bootout"))
        else:
            results.append(ActionResult("launchd-bootout", "skip", "launchctl not found"))
    else:
        systemctl = _systemctl_binary()
        if systemctl:
            rc, out, err = _run([systemctl, "--user", "stop", f"{agent.label}.service"])
            results.append(ActionResult("systemd-stop", "ok" if rc == 0 else "warn", err or out or "systemctl stop"))
        else:
            results.append(ActionResult("systemd-stop", "skip", "systemctl not found"))
    podman = _podman_binary()
    if podman:
        rc, out, err = _run([podman, "--connection", agent.podman_connection, "stop", "--ignore", agent.container_name], timeout=20)
        results.append(ActionResult("podman-stop", "ok" if rc == 0 else "warn", err or out or "podman stop"))
    print(f"stopped {agent.name}")
    return _emit_results(results)


def restart(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "restart")
    if not allowed:
        print("would stop then start the local agent")
        return 0
    stop_rc = stop(argparse.Namespace(agent=agent.name, execute=True, policy_ok=True))
    start_rc = start(argparse.Namespace(agent=agent.name, execute=True, policy_ok=True))
    return max(stop_rc, start_rc)


def quarantine(args: argparse.Namespace) -> int:
    agent = _agent_or_error(args.agent)
    if not (args.execute and args.policy_ok):
        output = _expand(args.output_dir)
        print(f"planned quarantine: {agent.name}")
        print(f"would capture evidence and move writable service definitions under: {output}")
        print("mutation not executed; pass --execute --policy-ok to allow guarded local changes")
        return 0
    qdir, results = _quarantine_agent(agent, _expand(args.output_dir))
    print(f"quarantined {agent.name}: {qdir}")
    return _emit_results(results)


def uninstall(args: argparse.Namespace) -> int:
    agent, allowed = _guarded_mutation(args, "uninstall")
    if not allowed:
        print("would stop service and move user-owned generated files into quarantine")
        return 0
    if not args.no_quarantine:
        qdir, results = _quarantine_agent(agent, _expand(args.output_dir))
        print(f"quarantined before uninstall: {qdir}")
        return _emit_results(results)
    results = [
        _move_if_exists(_expand(agent.user_plist), _expand(args.output_dir) / f"{agent.label}.plist.disabled", "move-user-plist"),
        _move_if_exists(_launcher_path(agent), _expand(args.output_dir) / f"{agent.name}-launch.disabled", "move-launcher"),
        _move_if_exists(_systemd_user_unit_path(agent), _expand(args.output_dir) / f"{agent.label}.service.disabled", "move-systemd-unit"),
    ]
    print(f"uninstalled {agent.name}")
    return _emit_results(results)


def local_runtime_doctor(_args: argparse.Namespace) -> int:
    print("SourceOS local runtime doctor")
    worst = 0
    for agent in DEFAULT_AGENTS.values():
        print(f"\n## {agent.name}")
        worst = max(worst, _print_checks(collect_checks(agent)))
    return worst


def build_parser(prog: str = "sourceos-agent") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="SourceOS local-agent runtime CLI")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    sub.add_parser("list", help="List known local agents").set_defaults(func=list_agents)

    for name, func, help_text in [
        ("preflight", preflight, "Run local-agent preflight checks"),
        ("doctor", doctor, "Run local-agent doctor checks"),
        ("status", status, "Print local-agent status"),
        ("logs", logs, "Tail local-agent app log"),
        ("install", install, "Plan or execute local-agent install"),
        ("stage", stage, "Plan or execute stage-only service generation"),
        ("start", start, "Plan or execute local-agent start"),
        ("stop", stop, "Plan or execute local-agent stop"),
        ("restart", restart, "Plan or execute local-agent restart"),
        ("quarantine", quarantine, "Plan or execute local-agent quarantine"),
        ("uninstall", uninstall, "Plan or execute local-agent uninstall"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("agent", choices=sorted(DEFAULT_AGENTS), help="Local agent name")
        if name == "logs":
            p.add_argument("--lines", type=int, default=80, help="Number of log lines to print")
        if name in {"install", "stage", "start", "stop", "restart", "quarantine", "uninstall"}:
            p.add_argument("--execute", action="store_true", default=False, help="Execute guarded local mutation")
            p.add_argument("--policy-ok", action="store_true", default=False, help="Confirm policy approval")
        if name == "install":
            p.add_argument("--force", action="store_true", default=False, help="Install service files even if runtime preflight blocks start")
        if name in {"stage", "quarantine", "uninstall"}:
            p.add_argument(
                "--output-dir",
                default="~/Desktop/sourceos-quarantine" if name != "stage" else "~/Desktop/sourceos-agent-stage",
                help="Directory where generated/evidence folders are created",
            )
        if name == "uninstall":
            p.add_argument("--no-quarantine", action="store_true", default=False, help="Move generated files without evidence capture")
        p.set_defaults(func=func)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
