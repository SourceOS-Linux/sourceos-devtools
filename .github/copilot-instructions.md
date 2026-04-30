Use the GitHub issue body as the source of truth.

Before editing:
1. Read the issue.
2. Inspect the repository.
3. Identify validation commands.
4. Keep the PR bounded.

When implementing:
- Prefer existing repository patterns.
- Add tests, fixtures, or validators with implementation changes.
- Do not invent release URLs, checksums, SBOMs, or provenance.
- Do not commit secrets, tokens, credentials, private keys, model weights, datasets, or training runs.
- Keep client-side tooling separate from backend services.
- For host-control helpers, implement dry-run and evidence inspection first.

When opening the PR:
- Link the issue.
- Include validation evidence.
- List known gaps.
- State non-goals preserved.
- Do not mark ready if validation did not run.
