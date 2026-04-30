.PHONY: validate

validate:
	@test -f README.md
	@test -f AGENTS.md
	@test -f .github/copilot-instructions.md
	@test -f docs/DEVTOOLS_SCOPE.md
	@test -f repo.maturity.yaml
	@python3 - <<'PY'
import pathlib
for path in [
    'README.md',
    'AGENTS.md',
    '.github/copilot-instructions.md',
    'docs/DEVTOOLS_SCOPE.md',
    'repo.maturity.yaml',
]:
    text = pathlib.Path(path).read_text()
    if not text.strip():
        raise SystemExit(f'{path} is empty')
print('OK: sourceos-devtools validation')
PY
