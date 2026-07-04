# SourceOS Devtools install and smoke guide

This guide covers the current Portable AI Kit scaffold in `sourceos-devtools`.

## Local source checkout

Run from the repository root:

```bash
python3 bin/sourceosctl portable-ai profiles
python3 bin/sourceosctl portable-ai preflight /tmp/SOURCEOS_AI --profile tiny-router
python3 bin/sourceosctl portable-ai prepare /tmp/SOURCEOS_AI --profile tiny-router --dry-run
python3 bin/sourceosctl portable-ai start-plan /tmp/SOURCEOS_AI --provider ollama-compatible --surface turtleterm
python3 bin/sourceosctl portable-ai stop-plan /tmp/SOURCEOS_AI --provider ollama-compatible
python3 bin/sourceosctl portable-ai byom verify /tmp/SOURCEOS_AI ./models/example.gguf --name example
```

The default posture is evidence-first and non-mutating. prompt egress is denied by default. Tool use is denied by default. Runtime start and stop commands emit plans; they do not launch or stop a provider.

## Homebrew scaffold

Before tap promotion, use the repository-local formula for syntax and smoke validation only:

```bash
brew install --HEAD https://raw.githubusercontent.com/SourceOS-Linux/sourceos-devtools/main/packaging/homebrew/Formula/sourceos-devtools.rb
```

After tap promotion:

```bash
brew install SourceOS-Linux/tap/sourceos-devtools
```

## Validation

```bash
python3 -m unittest discover -s tests -v
make validate
python3 scripts/validate_packaging.py
```

The packaging scaffold must not download model weights, call external providers, start local runtimes, store prompt bodies, or bypass Agent Machine / policy-gated runtime activation.
