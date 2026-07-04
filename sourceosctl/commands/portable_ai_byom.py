from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _print(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def verify(args) -> int:
    model_file = Path(args.model_file).expanduser().resolve()
    target_root = Path(args.target_root).expanduser().resolve()
    if not model_file.exists() or not model_file.is_file():
        raise SystemExit(f"model file not found: {model_file}")
    digest = hashlib.sha256()
    with model_file.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    slug = args.name or model_file.stem
    payload = {
        "type": "PortableAIByomVerification",
        "targetRoot": str(target_root),
        "modelFile": str(model_file),
        "name": slug,
        "packId": args.pack_id or f"urn:srcos:model-carry-pack:byom-{slug}",
        "displayName": args.display_name or slug,
        "sha256": digest.hexdigest(),
        "sizeBytes": model_file.stat().st_size,
        "licenseRef": args.license_ref,
        "sourceNote": args.source_note,
        "taskClasses": args.task_class or ["operator-selected"],
        "wouldCopy": bool(args.copy),
        "wouldWriteManifest": bool(args.execute),
        "routeEligibleBeforeReview": False,
        "promptEgressDefault": "deny",
        "toolUseDefault": "deny",
    }
    if args.execute and not args.policy_ok:
        raise SystemExit("--execute requires --policy-ok")
    return _print(payload)
