.PHONY: validate test scan-local-persistence validate-local-agents validate-local-agent-templates check-local-agent-drift validate-reasoning-cli validate-portable-ai validate-packaging

validate: test scan-local-persistence validate-local-agents validate-local-agent-templates check-local-agent-drift validate-reasoning-cli validate-portable-ai validate-packaging
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

check-local-agent-drift:
	@python3 scripts/check_local_agent_registry_drift.py . --fail-on high

validate-reasoning-cli:
	@python3 bin/sourceosctl reasoning validate tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning inspect tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning replay-plan tests/fixtures/reasoning/deterministic >/dev/null
	@python3 bin/sourceosctl reasoning events tests/fixtures/reasoning/deterministic >/dev/null

validate-portable-ai:
	@python3 bin/sourceosctl portable-ai profiles >/dev/null
	@python3 bin/sourceosctl portable-ai preflight /tmp/SOURCEOS_AI --profile tiny-router >/dev/null
	@python3 bin/sourceosctl portable-ai prepare /tmp/SOURCEOS_AI --profile tiny-router --dry-run >/dev/null

validate-packaging:
	@python3 scripts/validate_packaging.py
