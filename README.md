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

The initial validation target checks repository metadata and JSON/YAML syntax where present. Implementation-specific validation should be added with each tool surface.
