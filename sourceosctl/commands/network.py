"""Network Door and Native Assistant Door helpers.

These commands are non-mutating. They render profile plans and evidence-shaped
summaries for enterprise/user network policy, firewalls, mesh bindings, BYOM
providers, and native assistant bridges. They do not modify firewall rules,
install mesh components, contact model providers, or invoke native assistants.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict


NETWORK_PROFILE_REF = "urn:srcos:network-access-profile:enterprise-and-user-default"
USER_FIREWALL_REF = "urn:srcos:firewall-binding-profile:macos-lulu-user-default"
ENTERPRISE_FIREWALL_REF = "urn:srcos:firewall-binding-profile:enterprise-gateway-default"
ISTIO_MESH_REF = "urn:srcos:mesh-binding-profile:istio-egress-default"
BYOM_PROVIDER_REF = "urn:srcos:external-model-provider-profile:user-openai-compatible"
APPLE_APP_INTENTS_REF = "urn:srcos:native-assistant-bridge-profile:apple-app-intents-default"


def _print_json(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _hash_text(value: str | None) -> str | None:
    if value is None:
        return None
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def doctor(args) -> int:
    """Inspect host networking posture without changing anything."""
    return _print_json(
        {
            "type": "NetworkDoorDoctor",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "host": {
                "system": platform.system(),
                "machine": platform.machine(),
            },
            "contracts": {
                "networkAccessProfileRef": NETWORK_PROFILE_REF,
                "userFirewallBindingRef": USER_FIREWALL_REF,
                "enterpriseFirewallBindingRef": ENTERPRISE_FIREWALL_REF,
                "meshBindingRef": ISTIO_MESH_REF,
                "byomProviderRef": BYOM_PROVIDER_REF,
                "nativeAssistantBridgeRef": APPLE_APP_INTENTS_REF,
            },
            "policy": {
                "mutatesFirewall": False,
                "installsMesh": False,
                "contactsExternalProvider": False,
                "invokesNativeAssistant": False,
                "defaultEgress": "deny",
            },
        }
    )


def plan(args) -> int:
    """Render a non-mutating network route plan."""
    destination = args.destination or "model-provider"
    destination_hash = _hash_text(destination)
    provider_ref = args.model_provider_ref or BYOM_PROVIDER_REF
    profile_ref = args.network_profile_ref or NETWORK_PROFILE_REF
    mesh_ref = args.mesh_binding_ref if args.mesh else None
    firewall_refs = [USER_FIREWALL_REF]
    if args.enterprise:
        firewall_refs.insert(0, ENTERPRISE_FIREWALL_REF)
    decision = "deny" if not args.allow_listed else "allow-with-policy"
    return _print_json(
        {
            "type": "NetworkDoorPlan",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "scope": args.scope,
            "destinationHash": destination_hash,
            "destinationStored": False,
            "decision": decision,
            "networkAccessProfileRef": profile_ref,
            "firewallBindingRefs": firewall_refs,
            "meshBindingRef": mesh_ref,
            "modelProviderRef": provider_ref,
            "enterpriseProfileEnabled": args.enterprise,
            "userProfileEnabled": True,
            "policy": {
                "enterprisePrecedence": True,
                "userCanBeStricter": True,
                "promptEgressDefault": "deny",
                "hostedFallbackRequiresPolicy": True,
            },
            "evidence": {
                "emitNetworkDecision": True,
                "emitFirewallBinding": True,
                "emitMeshBinding": bool(mesh_ref),
                "emitModelProviderRoute": True,
                "redactDestinationPath": True,
            },
        }
    )


def provider_plan(args) -> int:
    """Render BYOM/external model provider profile plan without contacting it."""
    return _print_json(
        {
            "type": "ExternalModelProviderPlan",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "providerRef": args.provider_ref or BYOM_PROVIDER_REF,
            "providerClass": args.provider_class,
            "owner": args.owner,
            "networkAccessProfileRef": args.network_profile_ref or NETWORK_PROFILE_REF,
            "firewallBindingRef": args.firewall_binding_ref or USER_FIREWALL_REF,
            "meshBindingRef": args.mesh_binding_ref,
            "contactsProvider": False,
            "storesPrompt": False,
            "storesCompletion": False,
            "promptEgressDefault": "allow-with-policy" if args.allow_egress else "deny",
            "authInline": False,
            "authRefRequired": True,
            "evidence": {
                "emitRouteDecision": True,
                "emitNetworkDecision": True,
                "emitProviderHealth": True,
                "promptHashOnly": True,
            },
        }
    )


def native_assistant_plan(args) -> int:
    """Render a native assistant bridge plan without invoking host assistant APIs."""
    return _print_json(
        {
            "type": "NativeAssistantBridgePlan",
            "capturedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "bridgeRef": args.bridge_ref or APPLE_APP_INTENTS_REF,
            "platform": args.platform,
            "bridgeClass": args.bridge_class,
            "operation": args.operation,
            "invokesAssistant": False,
            "promptHash": _hash_text(args.prompt) if args.prompt else None,
            "promptStored": False,
            "requiresUserConfirmation": args.operation not in {"open-workroom", "inspect-evidence"},
            "networkAccessProfileRef": args.network_profile_ref or NETWORK_PROFILE_REF,
            "modelRouteBindingRef": args.model_route_binding_ref,
            "policy": {
                "localOnlyDefault": True,
                "allowPromptEgress": False,
                "allowCrossDeviceHandoff": bool(args.allow_cross_device),
                "allowPersonalContextRead": False,
                "allowSideEffectsWithoutConfirmation": False,
                "rawAppDatabaseAccessAllowed": False,
            },
            "evidence": {
                "emitAssistantInvocation": True,
                "emitUserConfirmation": True,
                "emitRouteDecision": True,
                "emitNativeBridgeReceipt": True,
                "redactPromptText": True,
            },
        }
    )


def evidence_inspect(args) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: evidence file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    return _print_json(
        {
            "path": str(path),
            "type": payload.get("type"),
            "decision": payload.get("decision"),
            "destinationStored": payload.get("destinationStored"),
            "promptStored": payload.get("promptStored"),
            "networkAccessProfileRef": payload.get("networkAccessProfileRef"),
            "modelProviderRef": payload.get("modelProviderRef"),
            "bridgeRef": payload.get("bridgeRef"),
        }
    )
