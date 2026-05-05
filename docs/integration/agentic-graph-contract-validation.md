# Agentic Graph Contract Validation

Status: draft
Related spec: `SourceOS-Linux/sourceos-spec#94`
Related tracker: `SourceOS-Linux/sourceos-spec#86`

## Purpose

This document defines the first `sourceosctl` tooling slice for the SourceOS/SociOS local-first agentic graph foundation.

The M1 objective is intentionally bounded: validate `.sourceos/manifest.json`, scan repos for contract posture, and provide non-mutating doctor/explain commands before runtime sync, agent, browser, shell, or relay integrations begin.

## Commands

### Validate a contract file

```bash
python3 bin/sourceosctl contract validate .sourceos/manifest.json
python3 bin/sourceosctl contract validate .sourceos/manifest.json --json
```

The first validator pass checks JSON parseability and the minimum `SourceOSRepoManifest` shape.

### Scan one repo

```bash
python3 bin/sourceosctl repo scan .
python3 bin/sourceosctl repo scan . --json
```

The repo scanner checks for `.sourceos/manifest.json` and reports whether it is compliant, missing, or invalid.

### Scan an estate root

```bash
python3 bin/sourceosctl estate scan ~/dev
python3 bin/sourceosctl estate scan ~/dev --json
```

The estate scanner checks immediate child repos for `.sourceos/manifest.json` and reports each repo status.

### Inspect graph/sync posture

```bash
python3 bin/sourceosctl graph doctor
python3 bin/sourceosctl sync doctor
```

These are non-mutating posture probes. Runtime graph and sync backends are not configured in `sourceos-devtools` yet.

### Explain a policy/audit JSON file

```bash
python3 bin/sourceosctl policy explain path/to/decision-or-audit.json
```

This prints the available decision/outcome, reason, policy ID, and policy domain fields.

## M1 validation statuses

The scanner uses these status classes:

- `compliant`
- `missing-manifest`
- `invalid-manifest`

Future hardening should add:

- `partial`
- `missing-required-engine`
- `missing-policy-class`
- `missing-audit-events`
- `schema-version-mismatch`
- `authority-repo-mismatch`

## Current limitations

- The validator is dependency-light and does not yet perform full JSON Schema draft 2020-12 validation.
- Schema loading from `SourceOS-Linux/sourceos-spec` is not yet vendored or pinned.
- Estate scanning currently checks immediate child directories only.
- Runtime SourceGraph, SourceSync, SourcePolicy, and SourceChannel backends are not configured in this repo.

## Acceptance criteria for this slice

1. `sourceos-devtools` declares a `.sourceos/manifest.json`.
2. `sourceosctl contract validate` can validate the local manifest shape.
3. `sourceosctl repo scan` can classify a repo manifest.
4. `sourceosctl estate scan` can classify child repos with manifests.
5. `sourceosctl graph doctor`, `sourceosctl sync doctor`, and `sourceosctl policy explain` are present and non-mutating.
6. Tests cover manifest validation, repo scan, and doctor commands.
