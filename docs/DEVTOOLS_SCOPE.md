# SourceOS Developer and AI Operator Tools Scope

`sourceos-devtools` is the client/operator tooling home for SourceOS.

## Product boundary

This repo provides tools that help a user, operator, or agent interact with SourceOS lifecycle systems. It should feel like the SourceOS equivalent of a Linux-native developer tools bundle plus local AI operator kit.

It is not a model lab, backend service, or OS image repository.

## Owned surfaces

### Developer tooling

- Nix/devshell helpers.
- Workstation bootstrap helpers.
- SourceOS profile selection helpers.
- Local repo/config-source helpers.
- Release artifact inspection.
- Environment fingerprint utilities.

### AI operator tooling

- Lab/profile selector clients.
- Local model-service client utilities.
- Model-router policy inspection helpers.
- Guardrail/eval/evidence inspection helpers.
- Agent sandbox/run helper stubs.
- Proof bundle packaging and inspection.
- Local-to-mesh registration client stubs.

### NLBoot/operator tooling

- NLBoot dry-run evidence inspectors.
- Boot/recovery release artifact inspection.
- Adapter evidence inspection.
- Release-readiness check wrappers.

## Non-goals

This repository must not own:

- model weights;
- training datasets;
- training runs;
- lab-specific model implementations;
- model-router backend;
- guardrail-fabric backend;
- model-governance-ledger backend;
- SourceOS boot/recovery implementation;
- SourceOS image build state;
- web control plane backend;
- secrets, tokens, credentials, private keys, or device enrollment secrets.

## Initial CLI shape

The first CLI surface should be conservative:

```text
sourceosctl doctor
sourceosctl profiles list
sourceosctl nlboot evidence inspect <path>
sourceosctl release inspect <path>
sourceosctl fingerprint collect --dry-run
sourceosctl ai labs list
sourceosctl agents sandbox plan --dry-run
```

Implementation should start with read-only inspection and dry-run planning. Mutating commands require separate review.

## Integration map

| Capability | Canonical owner | Devtools role |
| --- | --- | --- |
| Boot/recovery client | `SociOS-Linux/nlboot` | inspect and wrap evidence paths |
| SourceOS schemas | `SourceOS-Linux/sourceos-spec` | consume schemas |
| SourceOS boot integration | `SourceOS-Linux/sourceos-boot` | operator helpers only |
| Homebrew installation | `SocioProphet/homebrew-prophet` | publish install surface metadata |
| Model routing | `SocioProphet/model-router` | client/policy inspection |
| Guardrails | `SocioProphet/guardrail-fabric` | client/policy inspection |
| Governance ledger | `SocioProphet/model-governance-ledger` | evidence inspection |
| Agent authority | `SocioProphet/agent-registry` | client/contract inspection |

## Maturity gates

### M1

- README and scope docs.
- Agent instructions.
- Validation target.
- Repo maturity record.
- Initial scaffold issue dispatched.

### M2

- Minimal CLI with read-only/dry-run commands.
- Fixtures for release/evidence inspection.
- CI validation.

### M3

- Installable package path.
- Homebrew integration.
- Nix/devshell support.
- SourceOS profile selector client.

### M4

- Integrated with SourceOS control plane and local mesh registration.
- Signed release artifacts and provenance.

### M5

- Production-grade workstation/operator toolkit.
