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
- Network Door, Firewall Door, Mesh Door, BYOM provider, and Native Assistant Door plan/probe helpers;
- guardrail/eval/evidence helpers;
- agent sandbox/run helpers;
- Local Model Door runtime detection and route planning helpers;
- Agent Machine local mount and secure host-interface helpers;
- Office Plane dry-run, guarded execution, inspection, and evidence helpers;
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
- secrets, tokens, credentials, private keys, or device-specific enrollment secrets;
- firewall mutation engines;
- service mesh installers;
- native assistant runtime adapters.

## sourceosctl CLI

`sourceosctl` is the guarded CLI surface for SourceOS developer and AI operator workflows. Commands are read-only or dry-run by default. Narrow local mutations require explicit `--execute --policy-ok` and emit evidence.

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
| `sourceosctl local-model doctor` | Inspect local model runtime and installed models without pulling weights or inference |
| `sourceosctl local-model profiles` | List SourceOS Local Model Door profile refs |
| `sourceosctl local-model plan --profile local-llama32-1b` | Render local model runtime plan without installing or running models |
| `sourceosctl local-model route --task-class office-assist` | Render hash-only model route decision under local-first policy |
| `sourceosctl local-model evidence inspect <path>` | Inspect local model route evidence JSON |
| `sourceosctl network doctor` | Inspect Network Door contract posture without changing firewall, mesh, or provider state |
| `sourceosctl network plan --destination <label>` | Render a hash-only Network Door route plan |
| `sourceosctl network provider` | Render a BYOM / external model provider plan without contacting the provider |
| `sourceosctl network evidence inspect <path>` | Inspect Network Door evidence JSON |
| `sourceosctl native-assistant plan` | Render a native assistant bridge plan without invoking host assistant APIs |
| `sourceosctl agent-machine mounts plan` | Render Agent Machine local mount plan for dev/docs/downloads roots (dry-run) |
| `sourceosctl agent-machine mounts init --dry-run` | Render mount initialization plan; no directories or mounts are created |
| `sourceosctl agent-machine mounts init --execute --policy-ok` | Create only scoped local output/download directories and emit AgentMachineMountEvidence |
| `sourceosctl agent-machine mounts inspect [--include-downloads]` | Inspect default/local Agent Machine mount posture |
| `sourceosctl agent-machine mounts evidence inspect <path>` | Inspect Agent Machine mount evidence JSON (read-only) |
| `sourceosctl office doctor` | Inspect local Office Plane backend availability, including LibreOffice detection |
| `sourceosctl office plan` | Render an OfficeArtifact-compatible workroom artifact plan |
| `sourceosctl office generate --dry-run` | Render an Office generation plan without writing files |
| `sourceosctl office generate --execute --policy-ok --format md|txt|json` | Write a guarded text/Markdown/JSON artifact and emit OfficeArtifactEvidence |
| `sourceosctl office generate --execute --policy-ok --format docx|xlsx|pptx` | Write a guarded minimal OOXML artifact and emit OfficeArtifactEvidence |
| `sourceosctl office convert <path> --to <format> --dry-run` | Render a LibreOffice-style conversion plan without writing files |
| `sourceosctl office convert <path> --to <format> --execute --policy-ok` | Run guarded local LibreOffice conversion and emit OfficeArtifactEvidence |
| `sourceosctl office inspect <path>` | Inspect a local office artifact file and hash it |
| `sourceosctl office evidence inspect <path>` | Inspect Office Plane evidence JSON (read-only) |

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
python3 bin/sourceosctl local-model doctor
python3 bin/sourceosctl local-model profiles
python3 bin/sourceosctl local-model plan --profile local-llama32-1b
python3 bin/sourceosctl local-model route --task-class office-assist --prompt "local prompt text is hashed only"
python3 bin/sourceosctl network doctor
python3 bin/sourceosctl network plan --destination models.enterprise.example
python3 bin/sourceosctl network plan --enterprise --mesh --allow-listed --destination models.enterprise.example
python3 bin/sourceosctl network provider --provider-class openai-compatible --owner user
python3 bin/sourceosctl native-assistant plan --operation open-workroom
python3 bin/sourceosctl native-assistant plan --operation create-office-artifact --prompt "local prompt text is hashed only"
python3 bin/sourceosctl agent-machine mounts plan
python3 bin/sourceosctl agent-machine mounts init --dry-run
python3 bin/sourceosctl agent-machine mounts init --execute --policy-ok --evidence-out ./mount-evidence.json
python3 bin/sourceosctl agent-machine mounts inspect --include-downloads
python3 bin/sourceosctl office doctor
python3 bin/sourceosctl office plan --artifact-type slide-deck --format pptx --title "Demo Deck"
python3 bin/sourceosctl office generate --dry-run --artifact-type document --format docx --title "Demo Report"
python3 bin/sourceosctl office generate --execute --policy-ok --artifact-type document --format md --title "Demo Report" --evidence-out ./office-evidence.json
python3 bin/sourceosctl office generate --execute --policy-ok --artifact-type document --format docx --title "Demo Report" --evidence-out ./office-docx-evidence.json
python3 bin/sourceosctl office generate --execute --policy-ok --artifact-type spreadsheet --format xlsx --title "Demo Workbook" --evidence-out ./office-xlsx-evidence.json
python3 bin/sourceosctl office generate --execute --policy-ok --artifact-type slide-deck --format pptx --title "Demo Deck" --evidence-out ./office-pptx-evidence.json
python3 bin/sourceosctl office convert ./example.docx --to pdf --dry-run
python3 bin/sourceosctl office convert ./example.docx --to pdf --execute --policy-ok --evidence-out ./office-convert-evidence.json
```

### Local Model Door defaults

The Local Model Door aligns with:

- `SourceOS-Linux/sourceos-model-carry` for local model profiles;
- `SocioProphet/model-router` for routing;
- `SocioProphet/model-governance-ledger` for personal tuning contracts;
- `SociOS-Linux/socios` for opt-in personalization orchestration.

Default profiles:

| Profile key | Model | Role |
| --- | --- | --- |
| `local-llama32-1b` | `llama3.2:1b` | laptop-safe router, triage, summarization, rewrite, Office assist |
| `local-llama32-3b` | `llama3.2:3b` | quality local fallback |

The Local Model Door does **not** pull model weights, start Ollama, run inference, send prompts off-device, or authorize tool use. `local-model route --prompt ...` emits only a SHA-256 prompt hash.

### Network Door, Mesh Door, BYOM, and Native Assistant Door defaults

The Network/Assistant Door slice aligns with `SourceOS-Linux/sourceos-spec`:

- `NetworkAccessProfile`
- `FirewallBindingProfile`
- `MeshBindingProfile`
- `ExternalModelProviderProfile`
- `NativeAssistantBridgeProfile`

Default refs:

| Purpose | Ref |
| --- | --- |
| Enterprise/user network stack | `urn:srcos:network-access-profile:enterprise-and-user-default` |
| User firewall profile | `urn:srcos:firewall-binding-profile:macos-lulu-user-default` |
| Enterprise firewall profile | `urn:srcos:firewall-binding-profile:enterprise-gateway-default` |
| Istio/Admiral-style mesh profile | `urn:srcos:mesh-binding-profile:istio-egress-default` |
| User BYOM OpenAI-compatible provider profile | `urn:srcos:external-model-provider-profile:user-openai-compatible` |
| Apple App Intents native assistant bridge profile | `urn:srcos:native-assistant-bridge-profile:apple-app-intents-default` |

The Network Door does **not** mutate firewall rules, install mesh components, contact external model providers, store credentials, or send prompts. Destination labels are represented as SHA-256 hashes in route plans.

The Native Assistant Door does **not** invoke Siri, App Intents, Shortcuts, Android intents, Windows shell integrations, browser extensions, or MCP/native bridge transports. It renders a bridge plan with prompt text redacted to a SHA-256 hash when provided.

Default policy posture:

- default egress is denied;
- BYOM provider auth must be a reference, never inline;
- enterprise firewall denies have precedence over user allows;
- user firewall profiles may be stricter than enterprise profiles;
- mesh binding and firewall binding are complementary, not interchangeable;
- prompt egress is denied by default;
- native assistant side effects require user confirmation;
- raw app database access is denied by default.

See `docs/integration/network-native-assistant-door.md`.

### Agent Machine local mount defaults

The first Agent Machine mount slice aligns with the SourceOS contracts in `SourceOS-Linux/sourceos-spec`:

- `AgentMachineLocalDataPlane`
- `AgentMachineMountPolicy`
- `TopoLVMPlacementProfile`

Default host roots:

| Purpose | Host path | Agent path | Posture |
| --- | --- | --- | --- |
| Code / repositories | `~/dev` | `/workspace/dev` | read/write; explicit workspace root |
| Generated documents / reports | `~/Documents/SourceOS/agent-output` | `/workspace/output` | read/write; created only by explicit guarded materialization |
| Browser downloads | `~/Downloads/SourceOS/agent-downloads` | `/workspace/downloads` | browser read/write; agent read-only |

The CLI does **not** mount `$HOME` wholesale and does **not** expose `.ssh`, `.gnupg`, browser profiles, keychains, cloud credential directories, token stores, or password stores by default.

Guarded materialization creates only the declared `createIfMissing` folders. It does not create Podman machines, Podman bind mounts, containers, or background services.

TopoLVM is treated as a Linux cluster-local backend profile for the same logical mount contract. It is not used for macOS/APFS local mode and it is not represented as cross-node shared storage.

### Office Plane local defaults

The Office Plane aligns with `SocioProphet/prophet-workspace`:

- `ProfessionalWorkroom`
- `OfficeArtifact`

Default paths:

| Purpose | Host path | Agent path |
| --- | --- | --- |
| Workroom output | `~/Documents/SourceOS/agent-output` | `/workspace/output` |
| Browser downloads | `~/Downloads/SourceOS/agent-downloads` | `/workspace/downloads` |
| Code/templates | `~/dev` | `/workspace/dev` |

Backends are modeled as an abstraction:

- LibreOffice: local-first default for headless generation, inspection, render, and conversion.
- Collabora: future browser-collaboration / WOPI-style backend.
- ONLYOFFICE: future optional document-builder/editor backend.
- Microsoft Graph / Office 365 and Google Workspace: compatibility adapters, not core authority.
- SourceOS-native: future native document surfaces.

Guarded Office execution is intentionally bounded:

- `office generate --execute --policy-ok` writes `txt`, `md`, `json`, `docx`, `xlsx`, or `pptx` artifacts.
- DOCX/XLSX/PPTX generation uses a minimal dependency-light OOXML bootstrap builder, not a full template or collaboration engine.
- ODT/ODS/ODP and other binary formats remain conversion/backend territory until LibreOffice/Collabora/ONLYOFFICE template backends are hardened.
- `office convert --execute --policy-ok` uses local LibreOffice/`soffice` when available.
- All guarded Office execution emits or writes `OfficeArtifactEvidence`.
- Email sending, external publishing, and calendar modification remain policy-gated side effects and are not enabled here.

### Design constraints

All mutating commands require `--execute --policy-ok`. Commands that would mutate host state without both flags are rejected at runtime.

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
- `SourceOS-Linux/agent-term`: terminal-native SourceOS operator ChatOps console.
- `SociOS-Linux/workstation-contracts`: workstation/CI conformance contracts and IPC receipts.
- `SociOS-Linux/socios`: opt-in automation and personalization orchestration.
- `SocioProphet/prophet-workspace`: workspace product semantics, Professional Workrooms, and OfficeArtifact contracts.
- `SocioProphet/homebrew-prophet`: Homebrew install formulae.
- `SocioProphet/model-router`: governed model/service routing.
- `SocioProphet/guardrail-fabric`: guardrail policy client integration.
- `SocioProphet/model-governance-ledger`: evidence, consent, evaluation, promotion, and personalization governance records.
- `SocioProphet/agent-registry`: governed agent identity/tool-grant contracts.
- `SocioProphet/agentplane`: governed execution, placement, run, replay, and evidence.

## Validation

```bash
make validate
```

The validation target runs the unit test suite and checks repository metadata. All tests must pass.

```bash
make test   # run tests only
```
