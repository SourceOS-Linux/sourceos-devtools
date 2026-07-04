# Office Runtime Contract Evidence

`sourceosctl office` emits `OfficeArtifactEvidence` for guarded local Office Plane execution.  Guarded materialization now also projects that evidence into the open office runtime records owned by `SocioProphet/prophet-platform`.

## Scope

This bridge applies only when a local artifact is actually materialized and hashed.  Dry-run plans and failed conversions do not pretend to have committed runtime content.

Runtime contract records are attached under:

```json
{
  "officeRuntimeContracts": {
    "schemas": {},
    "officeDocumentRecord": {},
    "officeSessionRecord": {},
    "officeVersionRecord": {},
    "officeWritebackRecord": {}
  }
}
```

## Record mapping

| SourceOS evidence field | Runtime record target |
| --- | --- |
| `artifactId` | `document_id` |
| `workroomId` | `tenant_id` |
| `storageRef` | `storage_uri` / `content_ref` |
| `artifactHashes[0].sha256` | `content_hash` |
| `format` | `current_format` / `format` |
| `backend.engine` + `backend.mode` | `editor_binding` / `execution_backend` |
| `operation` | `capture_source` / `writeback.operation` |

## Closed-provider boundary

The SourceOS CLI local execution path does not use Google Workspace, Microsoft 365, Microsoft Graph, Apple iCloud, or Apple Notes as runtime authority.

`remote-api` defaults to `sourceos-remote`, not Microsoft Graph.  Closed-provider adapters belong to migration/import/export paths governed elsewhere, not local guarded Office evidence.

## Validation

```bash
make test
```

The tests verify:

- materialized guarded Office artifacts include runtime contract records;
- Microsoft Graph is not treated as an open SourceOS execution backend;
- no runtime records are emitted without a materialized artifact hash;
- `office evidence inspect` handles evidence containing runtime contracts.
