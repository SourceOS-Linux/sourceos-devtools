# SourceOS Developer and AI Operator Tools

`sourceos-devtools` is the installable SourceOS developer/operator toolkit surface.

It is the home for Linux-native developer tooling, AI operator tooling, lab profile selection, Nix/devshell orchestration, NLBoot/operator helpers, release tooling, local AI governance utilities, workstation bootstrap flows, and Portable AI Kit preparation flows.

## Scope

This repository owns client-side and workstation-side tooling, not the platform backends.

It should contain:

- `sourceosctl` / operator CLI scaffolding;
- Nix/devshell orchestration helpers;
- NLBoot dry-run and evidence inspection helpers;
- lab/profile selection utilities;
- local model-service client helpers;
- model-router client utilities;
- Portable AI Kit preflight, prepare, BYOM verification, launch-plan, inspect, and evidence helpers;
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

## Portable AI Kit

Portable AI Kit is the pocketable local-AI appliance mode for SourceOS: prepare a USB drive or portable SSD once, carry a governed local AI workstation, and run it on a supported host without sending prompts or chat state off-device by default.

Quick demo path from a checkout:

```bash
python3 bin/sourceosctl portable-ai profiles
python3 bin/sourceosctl portable-ai preflight /Volumes/SOURCEOS_AI
python3 bin/sourceosctl portable-ai prepare /Volumes/SOURCEOS_AI --profile laptop-safe --dry-run
python3 bin/sourceosctl portable-ai prepare /Volumes/SOURCEOS_AI --profile laptop-safe --execute --policy-ok --evidence-out ./portable-ai-evidence.json
python3 bin/sourceosctl portable-ai start-plan /Volumes/SOURCEOS_AI --surface turtleterm
python3 bin/sourceosctl portable-ai inspect /Volumes/SOURCEOS_AI
```

BYOM GGUF/local model verification path:

```bash
python3 bin/sourceosctl portable-ai prepare /Volumes/SOURCEOS_AI --profile byom-gguf --execute --policy-ok
python3 bin/sourceosctl portable-ai byom verify /Volumes/SOURCEOS_AI ./models/example.gguf --name example --license-ref operator-attestation-required
python3 bin/sourceosctl portable-ai byom verify /Volumes/SOURCEOS_AI ./models/example.gguf --name example --license-ref operator-attestation-required --execute --policy-ok --evidence-out ./byom-evidence.json
```

BYOM verification hashes a local file, records size and SHA-256, and emits a `ModelCarryPack` manifest. It does **not** download a model, contact a provider, start a runtime, grant network, grant tool use, or store prompt bodies.

Portable AI Kit does **not** download model weights implicitly, start local daemons implicitly, run inference during preflight, or authorize prompt egress by default. Runtime activation belongs to Agent Machine. Model pack definitions belong to `SourceOS-Linux/sourceos-model-carry`. Routing belongs to `SocioProphet/model-router` under Policy Fabric posture.

Default profiles:

| Profile key | Purpose | Minimum free space | Default posture |
| --- | --- | --- | --- |
| `tiny-router` | Routing, triage, rewrite, summarization | 8 GB | local-only, no tools |
| `laptop-safe` | Offline fallback, Office assist, privacy-first chat | 16 GB | prompt egress denied |
| `office-local` | Office Plane summarization and artifact drafting | 32 GB | workroom-scoped host writes |
| `code-local` | Repo triage and local coding assistance | 32 GB | repo-scoped host writes |
| `field-kit` | Field/operator portable SSD kit | 64 GB | evidence-first |
| `byom-gguf` | Bring-your-own GGUF import profile | varies | hash required before eligibility |

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
- `SourceOS-Linux/sourceos-model-carry`: local model profiles and carry-layer service refs.
- `SourceOS-Linux/agent-machine`: governed local runtime activation, teardown, and evidence receipts.
- `SourceOS-Linux/TurtleTerm`: first-class terminal surface for Portable AI Kit.
- `SourceOS-Linux/agent-term`: terminal-native SourceOS operator ChatOps console.
- `SocioProphet/homebrew-prophet`: Homebrew install formulae.
- `SocioProphet/model-router`: governed model/service routing.
- `SocioProphet/guardrail-fabric`: guardrail policy client integration.
- `SocioProphet/model-governance-ledger`: evidence and promotion records.
- `SocioProphet/agent-registry`: governed agent identity/tool-grant contracts.

## Validation

```bash
make validate
```

The validation target checks repository metadata and runs the unit test suite. Implementation-specific validation should be added with each tool surface.
