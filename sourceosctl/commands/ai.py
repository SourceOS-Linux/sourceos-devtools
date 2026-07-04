"""ai command: AI operator utilities."""

_STUB_LABS = [
    {"name": "local-inference", "status": "available", "description": "Local model inference lab"},
    {"name": "model-router", "status": "stub", "description": "Governed model routing lab (client stub)"},
    {"name": "guardrail-fabric", "status": "stub", "description": "Guardrail policy inspection lab (client stub)"},
]


def list_labs(args) -> int:
    """List available AI labs. Read-only."""
    print("Available AI labs (stub):")
    for lab in _STUB_LABS:
        print(f"  {lab['name']:<22} [{lab['status']:<9}]  {lab['description']}")
    return 0
