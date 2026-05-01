# SourceOS Developer and AI Operator Tools

`sourceos-devtools` is the installable SourceOS developer/operator toolkit surface.

It is the home for Linux-native developer tooling, AI operator tooling, lab profile selection, Nix/devshell orchestration, NLBoot/operator helpers, release tooling, local AI governance utilities, and workstation bootstrap flows.

## Scope

This repository owns client-side and workstation-side tooling, not the platform backends.

It should contain:

- `sourceosctl` / operator CLI scaffolding;
- Nix/devshell orchestration helpers;
- NLBoot dry-run and evidence inspection helpers;
- lab/profile selection utilities;
- local model-service client helpers;
- model-router client utilities;
- guardrail/eval/evidence helpers;
- agent sandbox/run helpers;
- fingerprint and proof bundle tools;
- local-to-mesh registration helpers;
- release/operator install scripts.

It should not contain:

- model weights;
- training runs;
- datasets;
- lab implementations;
- model-governance-ledger backend;
- model-router backend;
- web control plane backend;
- SourceOS image build state;
- secrets, tokens, credentials, private keys, or device-specific enrollment secrets.

## sourceosctl CLI

`sourceosctl` is the read-only/dry-run CLI surface for SourceOS developer and AI operator workflows.

### Usage

```text
sourceosctl [--version] <command> [<subcommand>] [options]
```

### Commands

| Command | Description |
| --- | --- |
| `sourceosctl doctor` | Run environment health checks (read-only) |
| `sourceosctl profiles list` | List available SourceOS profiles (read-only) |
| `sourceosctl nlboot evidence inspect <path>` | Inspect a NLBoot evidence JSON file (read-only) |
| `sourceosctl nlboot evidence inspect --validate <path>` | Inspect and validate a NLBoot evidence file against its bundled schema (read-only) |
| `sourceosctl nlboot evidence validate <path>` | Validate a NLBoot evidence file against its bundled JSON Schema (read-only) |
| `sourceosctl release inspect <path>` | Inspect a release artifact JSON file (read-only) |
| `sourceosctl release inspect-archive <path>` | Inspect a NLBoot release archive directory for required files (read-only) |
| `sourceosctl fingerprint collect --dry-run` | Print environment fingerprint fields (dry-run only) |
| `sourceosctl ai labs list` | List available AI labs (read-only) |
| `sourceosctl agents sandbox plan --dry-run` | Print agent sandbox plan (dry-run only) |

### Running from the repo

```bash
python3 bin/sourceosctl --help
python3 bin/sourceosctl doctor
python3 bin/sourceosctl profiles list
python3 bin/sourceosctl nlboot evidence inspect fixtures/sample_nlboot_evidence.json
python3 bin/sourceosctl nlboot evidence inspect --validate fixtures/sample_nlboot_evidence.json
python3 bin/sourceosctl nlboot evidence validate fixtures/sample_nlboot_evidence.json
python3 bin/sourceosctl release inspect fixtures/sample_release.json
python3 bin/sourceosctl release inspect-archive fixtures/nlboot_release_valid
python3 bin/sourceosctl fingerprint collect --dry-run
python3 bin/sourceosctl ai labs list
python3 bin/sourceosctl agents sandbox plan --dry-run
```

### Design constraints

All commands in the current surface are **read-only or dry-run**. No mutating command is implemented. Commands that would mutate host state are explicitly rejected at runtime.

## First milestone

M1 is repo maturity and install surface definition:

1. document scope and repo boundaries;
2. add agent instructions;
3. add validation target;
4. add devtools scope contract;
5. define the initial CLI/tooling layout;
6. dispatch Copilot/Codex to scaffold the first bounded implementation PR.

## Integration homes

- `SociOS-Linux/nlboot`: boot/recovery client and evidence records.
- `SourceOS-Linux/sourceos-spec`: canonical SourceOS schemas and contracts.
- `SourceOS-Linux/sourceos-boot`: SourceOS boot/recovery integration.
- `SocioProphet/homebrew-prophet`: Homebrew install formulae.
- `SocioProphet/model-router`: governed model/service routing.
- `SocioProphet/guardrail-fabric`: guardrail policy client integration.
- `SocioProphet/model-governance-ledger`: evidence and promotion records.
- `SocioProphet/agent-registry`: governed agent identity/tool-grant contracts.

## Validation

```bash
make validate
```

The validation target runs the unit test suite and checks repository metadata. All tests must pass.

```bash
make test   # run tests only
```

