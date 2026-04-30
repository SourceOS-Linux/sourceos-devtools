# Agent Operating Instructions

Work issue-first.

Rules:
- One repo, one issue, one PR.
- Inspect the live repository before editing.
- Keep scope bounded to the issue body.
- Do not broaden scope without asking in the issue.
- Do not touch unrelated files.
- Do not claim production readiness unless acceptance criteria prove it.
- Include validation evidence in the PR body.
- Leave known gaps explicit.

PR body must include:
- What changed.
- Exact commands run.
- Pass/fail output summary.
- Known gaps.
- Anything blocked.

Never:
- Commit secrets, tokens, credentials, private keys, or device-specific enrollment secrets.
- Invent release URLs, checksums, SBOMs, or provenance.
- Commit model weights, datasets, training runs, or mutable model state.
- Claim backend authority from client-side scaffolding.

SourceOS devtools-specific rules:
- This repo owns installable developer and AI operator tooling.
- It does not own model labs, model weights, platform backends, or SourceOS image build state.
- Keep CLI/operator helpers separate from backend services.
- Add validation with every implemented surface.
- Prefer dry-run and evidence inspection paths before real host-changing helpers.

Validation:
```bash
make validate
```
