"""Registry-backed SourceOS local-agent CLI adapter.

This module lets the existing local-agent command implementation consume
`sourceosctl/local_agents/*.json` declarations without a risky large rewrite of
`sourceosctl.commands.local_agent`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Optional

from sourceosctl.commands import local_agent
from sourceosctl.local_agents import registry


def _record_to_agent(record: registry.LocalAgentRecord) -> local_agent.LocalAgent:
    return local_agent.LocalAgent(
        name=record.name,
        label=record.label,
        scope=record.scope,
        runtime=record.runtime,
        container_name=record.container_name,
        runtime_image=record.runtime_image,
        source_image=record.source_image,
        podman_connection=record.podman_connection,
        authfile=record.authfile,
        user_plist=record.user_plist,
        legacy_system_plist=record.legacy_system_plist,
        log_dir=record.log_dir,
        app_log=record.app_log,
    )


def load_registry_into_cli() -> dict[str, local_agent.LocalAgent]:
    records = registry.load_records()
    agents = {name: _record_to_agent(record) for name, record in records.items()}
    local_agent.DEFAULT_AGENTS.clear()
    local_agent.DEFAULT_AGENTS.update(agents)
    return agents


def _json_default(value):
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _emit_json(payload: object) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
    return 0


def _json_read_only(argv: list[str]) -> Optional[int]:
    if "--json" not in argv:
        return None
    clean = [item for item in argv if item != "--json"]
    agents = load_registry_into_cli()
    if not clean:
        return _emit_json({"agents": sorted(agents)})

    command = clean[0]
    if command == "list":
        return _emit_json({"agents": [asdict(agent) for agent in agents.values()]})

    if command in {"preflight", "doctor", "status"}:
        if len(clean) < 2:
            print(f"{command} --json requires an agent name", file=sys.stderr)
            return 2
        agent = local_agent.DEFAULT_AGENTS.get(clean[1])
        if not agent:
            print(f"unknown local agent: {clean[1]}", file=sys.stderr)
            return 2
        checks = local_agent.collect_checks(agent)
        return _emit_json(
            {
                "agent": asdict(agent),
                "command": command,
                "checks": [asdict(check) for check in checks],
                "ok": not any(check.status == "fail" for check in checks),
            }
        )

    print("--json is currently supported for list, preflight, doctor, and status", file=sys.stderr)
    return 2


def local_runtime_doctor(_args=None) -> int:
    load_registry_into_cli()
    return local_agent.local_runtime_doctor(_args)


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_rc = _json_read_only(args)
    if json_rc is not None:
        return json_rc
    load_registry_into_cli()
    return local_agent.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
