# Network Door and Native Assistant Door CLI boundary

This slice adds non-mutating SourceOS operator surfaces for the contract family defined in `SourceOS-Linux/sourceos-spec`:

- `NetworkAccessProfile`
- `FirewallBindingProfile`
- `MeshBindingProfile`
- `ExternalModelProviderProfile`
- `NativeAssistantBridgeProfile`

The implementation is intentionally a plan/probe surface. It does not modify firewall state, install service mesh components, contact model providers, start model calls, invoke Siri/App Intents/native assistant APIs, or change host networking.

## Command surface

```bash
sourceosctl network doctor
sourceosctl network plan --destination models.enterprise.example
sourceosctl network plan --enterprise --mesh --allow-listed --destination models.enterprise.example
sourceosctl network provider --provider-class openai-compatible --owner user
sourceosctl network evidence inspect ./network-evidence.json

sourceosctl native-assistant plan
sourceosctl native-assistant plan --operation create-office-artifact --prompt 'draft a local report'
sourceosctl native-assistant plan --platform cross-device --bridge-class mcp --operation handoff-to-agent-machine --allow-cross-device
```

## Boundary

| Surface | Owns | Does not own |
|---|---|---|
| `sourceosctl network ...` | Local rendering of network/firewall/mesh/BYOM route plans and evidence-shaped summaries. | Firewall mutation, mesh installation, VPN/proxy configuration, model-provider calls, credential storage. |
| `sourceosctl native-assistant ...` | Local rendering of native assistant bridge plans and evidence-shaped summaries. | Apple App Intents implementation, Siri invocation, Shortcuts execution, Android/Windows assistant APIs, cross-device transport. |

## Policy posture

- Default egress is `deny`.
- Destination text is represented as a SHA-256 hash in route plans.
- BYOM provider auth is always represented as a reference; credentials are never inlined.
- Enterprise firewall rules have precedence over user allow rules.
- User firewall profiles may be stricter than enterprise policy.
- Mesh binding and firewall binding are complementary, not interchangeable.
- Native assistant bridge calls are local-only by default.
- Prompt egress is denied by default.
- Cross-device handoff is disabled unless explicitly requested.
- Raw app database access is denied.
- Side effects require user confirmation in the bridge plan.

## Implementation owner split

| Repo | Role |
|---|---|
| `SourceOS-Linux/sourceos-spec` | Canonical Network/Mesh/BYOM/Native Assistant Door contracts. |
| `SourceOS-Linux/sourceos-devtools` | Local non-mutating `sourceosctl` probe and plan surface. |
| `SocioProphet/model-router` | Runtime route decisions for local, personal, hosted, enterprise, and BYOM model targets. |
| `SocioProphet/agentplane` | Evidence records when network/provider/native bridge plans participate in governed runs. |
| `SocioProphet/guardrail-fabric` | Policy decisions for prompt egress, hosted fallback, native assistant side effects, and external provider access. |
| `SocioProphet/sociosphere` | Topology validation and cross-repo dependency direction. |

## Current non-goals

- Do not vendor Istio, Admiral, LuLu, Cilium, or enterprise firewalls here.
- Do not modify host firewall state from this slice.
- Do not install or configure mesh control planes from this slice.
- Do not store or print provider credentials.
- Do not invoke native assistant APIs.
- Do not expose raw Apple Notes, Photos, mail stores, browser profiles, keychains, token stores, or security-material directories by default.

## Next implementation lanes

1. Add AgentPlane evidence schemas for `NetworkDoorPlanEvidence`, `ExternalModelProviderRouteEvidence`, and `NativeAssistantBridgeEvidence`.
2. Add model-router BYOM profile consumption and policy checks against `ExternalModelProviderProfile`.
3. Add AgentTerm `/network`, `/byom`, and `/native-assistant` event surfaces.
4. Add Homebrew formula tests for `sourceosctl network doctor` and `sourceosctl native-assistant plan`.
