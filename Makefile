.PHONY: validate test scan-local-persistence

validate: test scan-local-persistence
	@test -f README.md
	@test -f AGENTS.md
	@test -f .github/copilot-instructions.md
	@test -f docs/DEVTOOLS_SCOPE.md
	@test -f repo.maturity.yaml
	@python3 scripts/validate_scaffold.py

test:
	@python3 -m pip install --user jsonschema >/dev/null
	@python3 -m unittest discover -s tests -v

scan-local-persistence:
	@python3 scripts/scan_local_persistence.py . --fail-on none
