.PHONY: validate test scan-local-persistence validate-local-agents validate-local-agent-templates validate-reasoning-cli

validate: test scan-local-persistence validate-local-agents validate-local-agent-templates validate-reasoning-cli
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

validate-local-agents:
	@python3 scripts/validate_local_agents.py .

validate-local-agent-templates:
	@python3 scripts/validate_local_agent_templates.py .

validate-reasoning-cli:
	@python3 bin/sourceosctl reasoning validate tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning inspect tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning replay-plan tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning events tests/fixtures/reasoning/deterministic >/dev/null
