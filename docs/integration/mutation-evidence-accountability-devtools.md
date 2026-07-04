# Mutation and Evidence Accountability Devtools Integration

Status: Proposed
Canonical spec: https://github.com/SourceOS-Linux/sourceos-spec/pull/96
Tracking issue: https://github.com/SourceOS-Linux/sourceos-devtools/issues/25

## Purpose

This document defines the first `sourceos-devtools` integration slice for SourceOS Mutation and Evidence Accountability.

The canonical schemas, examples, anti-pattern fixtures, and validator live in `SourceOS-Linux/sourceos-spec`. This repository provides the operator/developer CLI wrapper so implementation repos can validate against one shared contract instead of copying schema logic.

## CLI surface

```bash
python3 bin/sourceosctl mutation-evidence plan
python3 bin/sourceosctl mutation-evidence inspect --spec-root ../sourceos-spec
python3 bin/sourceosctl mutation-evidence validate --spec-root ../sourceos-spec
python3 bin/sourceosctl mutation-evidence fixture-plan
```

## Commands

### `mutation-evidence plan`

Prints the integration plan, required canonical spec files, downstream implementation repos, and semantic guardrails.

### `mutation-evidence inspect`

Checks whether a local `sourceos-spec` checkout contains the required Mutation and Evidence Accountability files:

- base schema bundle;
- umbrella primitive schema bundle;
- valid example fixtures;
- invalid anti-pattern fixtures;
- canonical validator.

### `mutation-evidence validate`

Runs the canonical validator from the `sourceos-spec` checkout. The validator checks:

- base examples and anti-patterns;
- umbrella primitive examples and anti-patterns;
- no-visible-extension browser attribution guardrails;
- delegated I/O actor-chain completeness;
- diagnostic observer-effect clearance blocking;
- archive extraction path-boundary and cleanup accounting;
- blind/degraded/missing sensor compromise-clearance blocking.

### `mutation-evidence fixture-plan`

Prints the valid and invalid fixture classes that implementation repos should reproduce or consume.

## Guardrails

The devtools wrapper keeps five guardrails visible to all downstream implementation repos:

1. No clearance when sensors are blind, degraded, or missing.
2. No extension-primary browser attribution when extension inventory is `none_visible`.
3. No delegated mutation without a complete actor chain.
4. No archive extraction without path-boundary and cleanup accounting.
5. No diagnostic observer-effect clearance with partial or redacted evidence.

## Stack consumers

This integration slice prepares implementation work in:

- `SourceOS-Linux/BearBrowser`
- `SourceOS-Linux/TurtleTerm`
- `SourceOS-Linux/sourceos-shell`
- `SourceOS-Linux/sourceos-syncd`
- `SourceOS-Linux/sourceos-boot`
- `SocioProphet/prophet-platform`
- `SocioProphet/ontogenesis`
- `SocioProphet/exodus`

## Acceptance criteria

- `sourceosctl mutation-evidence plan` returns 0.
- `sourceosctl mutation-evidence inspect --spec-root <path>` fails when required spec files are missing.
- `sourceosctl mutation-evidence inspect --spec-root <path>` passes when required spec files exist.
- `sourceosctl mutation-evidence validate --spec-root <path>` returns the canonical validator exit code.
- Tests cover the command surface and validator propagation behavior.
