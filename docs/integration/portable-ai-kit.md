# SourceOS Portable AI Kit

SourceOS Portable AI Kit is the pocketable local-AI appliance mode for SourceOS.

The product promise is deliberately simple: prepare a USB drive or portable SSD once, carry a governed local AI workstation, and run it on a supported host without sending prompts or chat state off-device by default.

This workstream absorbs the useful product pattern from simple portable Ollama/AnythingLLM USB projects, but raises the bar to SourceOS requirements: signed manifests, explicit model provenance, policy gates, host-write auditability, secret-free evidence, and integration with Agent Machine, Local Model Door, model-router, AgentPlane, Policy Fabric, TurtleTerm, AgentTerm, and BearBrowser.

## Position

Portable AI Kit is not a new agent brain, model registry, or governance authority.

It is the installable workstation-side product surface for:

- portable-root preflight checks;
- portable model pack planning;
- USB/SSD layout materialization;
- runtime launch planning;
- zero-trace and host-write audit posture;
- local model route evidence;
- TurtleTerm/AgentTerm/BearBrowser launch handoff;
- Agent Machine runtime receipts.

## User-facing command surface

Initial commands:

```text
sourceosctl portable-ai preflight <target-root> [--benchmark]
sourceosctl portable-ai profiles
sourceosctl portable-ai prepare <target-root> --profile laptop-safe --dry-run
sourceosctl portable-ai prepare <target-root> --profile laptop-safe --execute --policy-ok
sourceosctl portable-ai start-plan <target-root> --surface turtleterm
sourceosctl portable-ai inspect <target-root>
sourceosctl portable-ai evidence inspect <path>
```

All commands are read-only or dry-run by default. Materialization requires `--execute --policy-ok` and emits evidence. Runtime start remains a plan until Agent Machine activation gates are present.

## Portable root layout

```text
SOURCEOS_AI/
├── manifests/
│   ├── portable-ai-root.json
│   └── model-carry-pack.*.json
├── runtimes/
│   ├── ollama/
│   ├── llama-cpp/
│   └── openai-compatible-local/
├── models/
│   ├── blobs/
│   └── modelfiles/
├── cache/
│   ├── embeddings/
│   ├── retrieval/
│   └── prompt-prefix/
├── state/
│   ├── chat/
│   ├── workrooms/
│   └── routes/
├── surfaces/
│   ├── turtleterm/
│   ├── agent-term/
│   └── bearbrowser/
├── evidence/
│   ├── preflight/
│   ├── materialization/
│   ├── activation/
│   └── wipe/
└── tmp/
```

The portable root must not contain inline credentials, private keys, cloud tokens, or user enrollment secrets.

## Preflight requirements

`preflight` must check:

- target root exists or parent is writable;
- filesystem large-file support is suitable for GGUF/model blobs;
- free space meets selected model-pack class;
- mount is not read-only;
- optional read/write benchmark;
- CPU architecture;
- RAM class;
- local runtime availability;
- existing manifest validity;
- evidence directory writability;
- whether the target appears removable or explicitly user-approved.

The command must return structured JSON so TurtleTerm, AgentTerm, BearBrowser, and the website can render the same decision.

## Profiles

Initial portable profiles:

| Profile | Purpose | Minimum target | Default posture |
| --- | --- | --- | --- |
| `tiny-router` | local routing, triage, rewrite | 8 GB free | local-only, no tools |
| `laptop-safe` | general offline fallback and Office assist | 16 GB free | local-only, no prompt egress |
| `office-local` | Office Plane summarization and document assistance | 32 GB free | workroom-scoped |
| `code-local` | local coding assistant and repo triage | 32 GB free | repo-scoped |
| `field-kit` | portable SSD field/operator kit | 64 GB free | evidence-first |
| `byom-gguf` | bring-your-own GGUF import | varies | manifest + hash required |

## Security posture

Default policy:

- prompt egress denied;
- model downloads require explicit operator action;
- model blobs require signed or pinned-hash manifests;
- host `$HOME` writes denied by default;
- host cache writes denied by default;
- runtime ports bind to loopback only unless policy grants otherwise;
- tool use denied by default;
- wipe receipts required for zero-trace mode;
- evidence stores hashes and refs, not prompt bodies.

## Launch posture

A launch plan should describe what would start, not start it implicitly:

- runtime provider: Ollama-compatible, llama.cpp, MLX/oMLX compatibility, or OpenAI-compatible local server;
- model profile and local model reference;
- portable state root;
- localhost port binding;
- selected surface: TurtleTerm, AgentTerm, BearBrowser, or local web fallback;
- required Agent Machine activation decision;
- expected evidence outputs.

## Capability parity target

The first parity target is to match simple portable USB projects at the product surface while exceeding them on governance.

| Capability | Required SourceOS answer |
| --- | --- |
| USB/SSD preflight | `portable-ai preflight` with JSON evidence |
| Model menu | signed `ModelCarryPack` profiles |
| Custom GGUF | BYOM import plan with hash/license/provenance checks |
| Local chat UI | TurtleTerm plus local web fallback; optional AnythingLLM adapter |
| Ollama support | runtime profile, not sole authority |
| Offline mode | prompt egress denied and model route local-only by default |
| Zero trace | portable state root plus host-write audit and wipe receipt |
| Multi-platform | Linux-first, macOS/Windows compatibility as adapters |
| Safe shutdown | Agent Machine activation/teardown receipts |
| User clarity | one prepare path, one inspect path, one start plan |

## Acceptance criteria

M1 is complete when:

1. `sourceosctl portable-ai preflight` renders structured JSON without mutating the target.
2. `sourceosctl portable-ai profiles` lists built-in portable profiles.
3. `sourceosctl portable-ai prepare --dry-run` renders a portable-root materialization plan.
4. `sourceosctl portable-ai prepare --execute --policy-ok` creates only declared directories and writes evidence.
5. `sourceosctl portable-ai start-plan` renders a launch plan without starting daemons.
6. `sourceos-model-carry` owns the portable model-pack schema and examples.
7. `agent-machine` owns runtime activation and teardown evidence semantics.
8. README documents the one-command demo path.

M2 is complete when:

1. model-pack manifests include pinned hashes and license/provenance fields;
2. BYOM GGUF import validates file presence and hash before route eligibility;
3. TurtleTerm can consume `start-plan` output;
4. Agent Machine emits portable runtime receipts;
5. website/product docs present the portable kit as a first-class SourceOS capability.

## Integration homes

| Repo | Responsibility |
| --- | --- |
| `SourceOS-Linux/sourceos-devtools` | CLI, preflight, prepare, inspect, launch-plan surface |
| `SourceOS-Linux/sourceos-model-carry` | portable model-pack schemas, examples, provenance expectations |
| `SourceOS-Linux/agent-machine` | provider activation, teardown, cache/model residency receipts |
| `SourceOS-Linux/sourceos-spec` | promoted stable contracts |
| `SourceOS-Linux/TurtleTerm` | first-class terminal UI surface |
| `SourceOS-Linux/agent-term` | ChatOps/operator event surface |
| `SocioProphet/model-router` | governed local/hosted routing |
| `SocioProphet/policy-fabric` | side-effect and prompt-egress policy |
| `SocioProphet/agentplane` | run/evidence submission and replay |
| `SocioProphet/prophet-workspace` | workroom and artifact semantics |
