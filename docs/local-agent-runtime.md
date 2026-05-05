# SourceOS Local Agent Runtime CLI

`sourceos-agent` is the SourceOS developer/operator CLI for inspecting and safely managing local agents.

Canonical policy lives in `SourceOS-Linux/sourceos-spec/specs/local-agent-runtime.md`.

This repository owns the CLI implementation surface: preflight, doctor, status, logs, and guarded mutation plans for install/start/stop/restart/quarantine/uninstall.

## Why this exists

The first incident target is `node-commander`.

The original local runtime landed as a system-wide macOS LaunchAgent that invoked a Nix store wrapper, called Podman, depended on noninteractive registry authentication, wrote logs to `/tmp`, and repeatedly restarted when Podman/auth failed. The failure looked like suspicious unmanaged-Mac persistence.

`sourceos-agent` makes those failure modes visible and bounded.

## Current commands

```bash
python3 bin/sourceos-agent list
python3 bin/sourceos-agent preflight node-commander
python3 bin/sourceos-agent doctor node-commander
python3 bin/sourceos-agent status node-commander
python3 bin/sourceos-agent logs node-commander
python3 bin/sourceos-agent quarantine node-commander
python3 bin/sourceos-agent install node-commander
python3 bin/sourceos-agent start node-commander
python3 bin/sourceos-agent stop node-commander
python3 bin/sourceos-agent restart node-commander
python3 bin/sourceos-agent uninstall node-commander
```

The same surface is routed through `sourceosctl`:

```bash
python3 bin/sourceosctl local-agent list
python3 bin/sourceosctl local-agent doctor node-commander
python3 bin/sourceosctl doctor local-runtime
```

## Safety posture

Read-only commands:

- `list`
- `preflight`
- `doctor`
- `status`
- `logs`

Mutation commands are guarded. Without both flags, they print a plan only:

```bash
python3 bin/sourceos-agent quarantine node-commander
```

To permit a future guarded mutation implementation:

```bash
python3 bin/sourceos-agent quarantine node-commander --execute --policy-ok
```

The scaffold currently refuses partial mutation even with both flags until the full quarantine/install/start/stop implementations are added.

## Checks performed

`preflight`, `doctor`, and `status` inspect:

- agent declaration
- local runtime image policy
- source image provenance
- user LaunchAgent plist
- legacy system-wide LaunchAgent plist
- launchd registration state on macOS
- launchd disabled override on macOS
- Podman binary availability
- Podman machine/socket reachability
- local image presence
- container state including `Stopping` / `Removing`
- explicit empty authfile state
- host Docker credential-helper risk
- host containers auth registry risk
- log directory state

## node-commander default declaration

`node-commander` is declared as:

- scope: user
- runtime: podman
- label: `org.socioprophet.node-commander`
- runtime image: `localhost/socioprophet/node-commander:dev-boot`
- source image provenance: `us-central1-docker.pkg.dev/socioprophet-web/node-commander/node-commander:dev-boot`
- Podman connection: `podman-machine-default`
- runtime authfile: `~/.config/containers/empty-auth.json`
- user plist: `~/Library/LaunchAgents/org.socioprophet.node-commander.plist`
- legacy plist detector: `/Library/LaunchAgents/org.socioprophet.node-commander.plist`
- app log: `~/Library/Logs/SocioProphet/node-commander.log`

## Design constraints

`sourceos-agent` must not silently mutate host persistence.

Future mutating implementations must:

1. run preflight first;
2. stage artifacts before enabling them;
3. emit evidence;
4. support quarantine/rollback;
5. refuse unsafe persistence by default;
6. never depend on interactive credential-helper refresh in noninteractive runtime.

## Validation

```bash
make validate
```

This runs the unittest suite, including the local-agent scaffold tests.
