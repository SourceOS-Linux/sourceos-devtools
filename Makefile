.PHONY: validate test

validate: test
	@test -f README.md
	@test -f AGENTS.md
	@test -f .github/copilot-instructions.md
	@test -f docs/DEVTOOLS_SCOPE.md
	@test -f repo.maturity.yaml
	@python3 scripts/validate_scaffold.py

test:
	@python3 -m unittest discover -s tests -v
