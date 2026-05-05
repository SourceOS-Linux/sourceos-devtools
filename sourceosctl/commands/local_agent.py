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


def _home() -> str:
    return os.path.expanduser("~")


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


def _launchd_status(agent: LocalAgent) -> Check:
    if platform.system() != "Darwin":
        return Check("launchd", "skip", "not a Darwin host")
    launchctl = _launchctl_binary()
    if not launchctl:
        return Check("launchd", "fail", "launchctl not found")
    domain = f"gui/{os.getuid()}/{agent.label}"
    rc, out, err = _run([launchctl, "print", domain])
    if rc == 0:
        state = "unknown"
        runs = "unknown"
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.startswith("state ="):
                state = stripped.split("=", 1)[1].strip()
            if stripped.startswith("runs ="):
                runs = stripped.split("=", 1)[1].strip()
        return Check("launchd", "pass", f"service registered: state={state}; runs={runs}")
    return Check("launchd", "warn", err or out or "service not registered")


def _launchd_disabled_override(agent: LocalAgent) -> Check:
    if platform.system() != "Darwin":
        return Check("launchd-disabled-override", "skip", "not a Darwin host")
    launchctl = _launchctl_binary()
    if not launchctl:
        return Check("launchd-disabled-override", "fail", "launchctl not found")
    rc, out, err = _run([launchctl, "print-disabled", f"gui/{os.getuid()}"])
    if rc != 0:
        return Check("launchd-disabled-override", "warn", err or out or "unable to read disabled overrides")
    needle = f'"{agent.label}" => disabled'
    if needle in out:
        return Check(
            "launchd-disabled-override",
            "fail",
            "service label is disabled in launchd overrides",
            f"launchctl enable gui/{os.getuid()}/{agent.label}",
        )
    return Check("launchd-disabled-override", "pass", "no disabled override found")


def _plist_check(agent: LocalAgent) -> list[Check]:
    checks: list[Check] = []
    user_plist = _expand(agent.user_plist)
    legacy = pathlib.Path(agent.legacy_system_plist)
    if user_plist.exists():
        try:
            with user_plist.open("rb") as fh:
                payload = plistlib.load(fh)
            label = payload.get("Label")
            keepalive = payload.get("KeepAlive")
            stdout = payload.get("StandardOutPath")
            stderr = payload.get("StandardErrorPath")
            status = "pass" if label == agent.label else "fail"
            checks.append(Check("user-plist", status, f"{user_plist}; KeepAlive={keepalive}; stdout={stdout}; stderr={stderr}"))
            if keepalive is True:
                checks.append(Check("keepalive", "fail", "KeepAlive=true requires bounded restart policy"))
            else:
                checks.append(Check("keepalive", "pass", "KeepAlive is not enabled"))
            for key, value in {"stdout": stdout, "stderr": stderr}.items():
                if value and str(value).startswith("/tmp/"):
                    checks.append(Check(f"{key}-log", "fail", f"primary log path uses /tmp: {value}"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("user-plist", "fail", f"plist parse failed: {exc}"))
    else:
        checks.append(Check("user-plist", "warn", f"not installed: {user_plist}"))
    if legacy.exists():
        checks.append(
            Check(
                "legacy-system-plist",
                "fail",
                f"legacy system-wide user agent still exists: {legacy}",
                f"sourceos-agent quarantine {agent.name}",
            )
        )
    else:
        checks.append(Check("legacy-system-plist", "pass", "no legacy /Library/LaunchAgents plist found"))
    return checks


def _podman_checks(agent: LocalAgent) -> list[Check]:
    checks: list[Check] = []
    podman = _podman_binary()
    if not podman:
        return [Check("podman", "fail", "podman binary not found")]
    checks.append(Check("podman", "pass", podman))

    rc, out, err = _run([podman, "--connection", agent.podman_connection, "info"], timeout=12)
    if rc == 0:
        checks.append(Check("podman-socket", "pass", f"connection reachable: {agent.podman_connection}"))
    else:
        checks.append(
            Check(
                "podman-socket",
                "fail",
                err or out or "podman connection failed",
                f"podman machine start {agent.podman_connection}",
            )
        )

    rc, out, err = _run([podman, "--connection", agent.podman_connection, "image", "exists", agent.runtime_image], timeout=8)
    if rc == 0:
        checks.append(Check("runtime-image", "pass", f"local image present: {agent.runtime_image}"))
    else:
        checks.append(
            Check(
                "runtime-image",
                "fail",
                err or out or f"local image missing: {agent.runtime_image}",
                f"tag/pull image then run with local tag: {agent.runtime_image}",
            )
        )

    rc, out, err = _run(
        [
            podman,
            "--connection",
            agent.podman_connection,
            "ps",
            "-a",
            "--filter",
            f"name={agent.container_name}",
            "--format",
            "{{.Names}} {{.Status}}",
        ],
        timeout=8,
    )
    if rc == 0 and out:
        status = "warn" if "Stopping" in out or "Removing" in out else "pass"
        checks.append(Check("container-state", status, out))
    elif rc == 0:
        checks.append(Check("container-state", "warn", "container not present"))
    else:
        checks.append(Check("container-state", "warn", err or out or "unable to inspect container state"))

    return checks


def _auth_checks(agent: LocalAgent) -> list[Check]:
    checks: list[Check] = []
    authfile = _expand(agent.authfile)
    ok, detail = _authfile_is_empty_auth(authfile)
    checks.append(Check("runtime-authfile", "pass" if ok else "fail", f"{authfile}: {detail}"))

    docker_config = _expand("~/.docker/config.json")
    containers_auth = _expand("~/.config/containers/auth.json")
    if docker_config.exists():
        redacted = _redacted_json(docker_config)
        if "gcloud" in redacted or "credHelpers" in redacted:
            checks.append(
                Check(
                    "ambient-docker-auth",
                    "warn",
                    "host Docker config contains credential helpers; runtime must use explicit authfile",
                )
            )
        else:
            checks.append(Check("ambient-docker-auth", "pass", "no obvious credential helper risk"))
    else:
        checks.append(Check("ambient-docker-auth", "pass", "no ~/.docker/config.json found"))

    if containers_auth.exists():
        redacted = _redacted_json(containers_auth)
        if "us-central1-docker.pkg.dev" in redacted:
            checks.append(
                Check(
                    "ambient-containers-auth",
                    "warn",
                    "containers auth references Google Artifact Registry; runtime should use empty-authfile/local tag",
                )
            )
        else:
            checks.append(Check("ambient-containers-auth", "pass", "containers auth present without known registry risk"))
    else:
        checks.append(Check("ambient-containers-auth", "pass", "no ~/.config/containers/auth.json found"))
    return checks


def collect_checks(agent: LocalAgent) -> list[Check]:
    checks = [
        Check("agent", "pass", f"{agent.name}; scope={agent.scope}; runtime={agent.runtime}"),
        Check("runtime-image-policy", "pass" if agent.runtime_image.startswith("localhost/") else "fail", agent.runtime_image),
        Check("source-image-provenance", "pass", agent.source_image),
    ]
    checks.extend(_plist_check(agent))
    checks.append(_launchd_status(agent))
    checks.append(_launchd_disabled_override(agent))
    checks.extend(_podman_checks(agent))
    checks.extend(_auth_checks(agent))
    log_dir = _expand(agent.log_dir)
    checks.append(Check("log-dir", "pass" if log_dir.exists() else "warn", str(log_dir)))
    return checks


def _print_checks(checks: Iterable[Check]) -> int:
    worst = 0
    for check in checks:
        icon = {"pass": "ok", "warn": "warn", "fail": "fail", "skip": "skip"}.get(check.status, check.status)
        print(f"[{icon}] {check.name}: {check.detail}")
        if check.remediation:
            print(f"      remediation: {check.remediation}")
        if check.status == "fail":
            worst = 1
    return worst


def _write_text(path: pathlib.Path, content: str) -> ActionResult:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return ActionResult("write", "ok", f"wrote {path}", str(path))
    except Exception as exc:  # noqa: BLE001
        return ActionResult("write", "warn", f"could not write {path}: {exc}", str(path))


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

    # Move writable service definitions after evidence capture. System-wide legacy
    # plists may require sudo; in that case we report the warning and leave the
    # operator with a clear follow-up rather than silently failing.
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


def _guarded_mutation(args: argparse.Namespace, action: str) -> int:
    agent = _agent_or_error(args.agent)
    if not (args.execute and args.policy_ok):
        print(f"planned {action}: {agent.name}")
        print("mutation not executed; pass --execute --policy-ok to allow guarded local changes")
        return 0
    print(f"{action} is not yet implemented in this scaffold; refusing partial mutation", file=sys.stderr)
    return 1


def install(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "install")


def stage(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "stage")


def start(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "start")


def stop(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "stop")


def restart(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "restart")


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
    worst = 0
    for result in results:
        print(f"[{result.status}] {result.action}: {result.detail}")
        if result.status == "warn":
            worst = max(worst, 1)
    return worst


def uninstall(args: argparse.Namespace) -> int:
    return _guarded_mutation(args, "uninstall")


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
        if name == "quarantine":
            p.add_argument(
                "--output-dir",
                default="~/Desktop/sourceos-quarantine",
                help="Directory where quarantine evidence folders are created",
            )
        p.set_defaults(func=func)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
