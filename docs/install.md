# SourceOS Devtools Install Guide

This guide documents the install surface for `sourceos-devtools`, including SourceOS Portable AI Kit commands.

The install surface intentionally installs CLI/planning tools only. It does not install model weights, pull models, start local model runtimes, grant network access, or mutate a Portable AI Kit root by default.

## Direct Homebrew install

Before tap promotion, install from the repository formula:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/sourceos-devtools/main/packaging/homebrew/Formula/sourceos-devtools.rb
```

After tap promotion:

```bash
brew install SourceOS-Linux/tap/sourceos-devtools
```

Validate:

```bash
sourceosctl portable-ai profiles
sourceos-portable-ai profiles
```

## Checkout development flow

```bash
git clone https://github.com/SourceOS-Linux/sourceos-devtools.git
cd sourceos-devtools
python3 bin/sourceosctl portable-ai profiles
python3 -m unittest discover -s tests -v
```

## Portable AI Kit smoke test

Use a temporary or removable target root. The commands below do not download models or start daemons.

```bash
TARGET=/tmp/SOURCEOS_AI
python3 bin/sourceosctl portable-ai preflight "$TARGET"
python3 bin/sourceosctl portable-ai prepare "$TARGET" --profile laptop-safe --dry-run
python3 bin/sourceosctl portable-ai prepare "$TARGET" --profile laptop-safe --execute --policy-ok --evidence-out ./portable-ai-evidence.json
python3 bin/sourceosctl portable-ai start-plan "$TARGET" --provider ollama-compatible --surface turtleterm
python3 bin/sourceosctl portable-ai stop-plan "$TARGET" --provider ollama-compatible
python3 bin/sourceosctl portable-ai inspect "$TARGET"
```

## BYOM verification smoke test

```bash
TARGET=/tmp/SOURCEOS_AI
mkdir -p ./tmp-models
printf 'demo model bytes\n' > ./tmp-models/example.gguf
python3 bin/sourceosctl portable-ai prepare "$TARGET" --profile byom-gguf --execute --policy-ok
python3 bin/sourceosctl portable-ai byom verify "$TARGET" ./tmp-models/example.gguf --name example
python3 bin/sourceosctl portable-ai byom verify "$TARGET" ./tmp-models/example.gguf --name example --execute --policy-ok --evidence-out ./byom-evidence.json
```

BYOM verification hashes a local file, records file size and SHA-256, writes a `ModelCarryPack` manifest only with `--execute --policy-ok`, and records that no download occurred.

## Policy posture

Default posture:

- prompt egress is denied;
- tool use is denied;
- model downloads are explicit only;
- runtime activation remains Agent Machine gated;
- preflight is non-mutating unless `--benchmark` is requested;
- `--benchmark` writes and removes a temporary local file and records cleanup in evidence;
- runtime start/stop commands are plans only at this layer;
- local model file materialization requires `--execute --policy-ok`.

## Promotion path

1. Land the repo-local formula.
2. Validate direct formula install.
3. Promote formula into `SourceOS-Linux/tap` after release checks.
4. Add signed release artifacts and checksums once versioned packaging stabilizes.
