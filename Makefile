.PHONY: validate test validate-packaging

validate: test validate-packaging
	@test -f README.md
	@test -f docs/install.md
	@test -f docs/integration/portable-ai-kit.md
	@test -f packaging/homebrew/Formula/sourceos-devtools.rb

test:
	python3 -m unittest discover -s tests -v

validate-packaging:
	python3 scripts/validate_packaging.py
