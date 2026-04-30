"""profiles command: list available SourceOS profiles."""

_STUB_PROFILES = [
    {"name": "developer", "description": "Standard developer workstation profile"},
    {"name": "operator", "description": "AI operator / model-router profile"},
    {"name": "minimal", "description": "Minimal read-only inspection profile"},
]


def list_profiles(args) -> int:
    """List stub profiles. Read-only."""
    print("Available profiles (stub):")
    for profile in _STUB_PROFILES:
        print(f"  {profile['name']:<16} {profile['description']}")
    return 0
