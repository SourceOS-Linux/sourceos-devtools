# SourceOS Operation Conformance Runner

Status: initial implementation

Issue: SourceOS-Linux/sourceos-devtools#19

## Purpose

`tools/sourceos_operation_conformance.py` validates Workspace Operation Plane fixture bundles from `SocioProphet/prophet-core-contracts` or from adapter repos that implement the same fixture shape.

The runner is intentionally usable with only the Python standard library for structural checks. If the optional `jsonschema` package is installed, it also runs schema validation against the contract schemas.

## Default layout

The expected local development layout is:

```text
~/dev/sourceos-devtools
~/dev/prophet-core-contracts
```

From `~/dev/sourceos-devtools`, run:

```bash
python3 tools/sourceos_operation_conformance.py \
  --contracts-dir ../prophet-core-contracts
```

For structural-only checks:

```bash
python3 tools/sourceos_operation_conformance.py \
  --contracts-dir ../prophet-core-contracts \
  --structural-only
```

For explicit paths:

```bash
python3 tools/sourceos_operation_conformance.py \
  --examples-dir ../prophet-core-contracts/examples/workspace-operation \
  --schemas-dir ../prophet-core-contracts/schemas
```

## What structural validation checks

- Every fixture is operation-centered.
- `operation_id`, `operation_type`, `schema_version`, and `idempotency_key` are present.
- Listed task IDs have corresponding task objects.
- Listed artifact IDs have corresponding artifact objects.
- Listed decision IDs have corresponding decision objects.
- Listed policy gate IDs have corresponding policy gate objects.
- Retryable tasks have idempotency keys.
- Active artifacts are admitted or activated.
- Quarantined artifacts are not active.
- Pending decisions include options.
- Blocking or decision-requiring gates include responsible actor and remediation options.
- `awaiting_decision` operations include decisions.
- `blocked` operations include policy gates.

## Optional JSON Schema validation

If `jsonschema` is installed, the runner also validates objects against:

- `schemas/workspace-operation.schema.json`
- `schemas/operation-task-event.schema.json`
- `schemas/artifact-admission.schema.json`
- `schemas/decision-policy-adapter.schema.json`

This optional path is the bridge between the lightweight contract validation currently in `prophet-core-contracts` and a reusable SourceOS conformance runner that downstream repos can invoke.

## Next work

- Add a CLI wrapper once the repo's command layout is standardized.
- Add adapter scaffolding commands.
- Add redaction CLI for diagnostic bundles.
- Emit machine-readable validation reports.
- Add fixture-generation helpers for terminal, browser, local agent-machine, sync, and release operations.
