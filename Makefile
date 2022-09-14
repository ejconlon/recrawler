# Disable default make target
.PHONY: default
default:
	echo "No default target"

# Create the virtual environment
.PHONY: venv
venv:
	python3 -m venv --upgrade-deps .venv
	.venv/bin/python3 -m pip install wheel -r dev-requirements.txt -r requirements.txt

# Format - for now just sort imports
.PHONY: format
format:
	.venv/bin/python3 -m isort --settings-path=setup.cfg recrawler

# Typecheck with mypy
.PHONY: typecheck
typecheck:
	.venv/bin/python3 -m mypy -p recrawler

# Lint with flake8
.PHONY: lint
lint:
	.venv/bin/python3 -m flake8 --config=setup.cfg recrawler

# Unit test with pytest
.PHONY: unit
unit:
	if [ -d tests ]; then .venv/bin/python3 -m pytest tests; fi

# Run all tests
.PHONY: test
test: lint typecheck unit

# Clean most generated files (+ venv)
.PHONY: clean
clean:
	rm -rf .venv .mypy_cache .pytest_cache *.egg-info

# Package into a zip file
.PHONY: package
package:
	./scripts/package.sh

# Build with docker
.PHONY: docker-build
docker-build:
	cd docker && docker build -t recrawler-build .

# Package with docker
.PHONY: docker-package
docker-package: docker-build
	docker run -it -v ${PWD}:/project -w /project recrawler-build /bin/bash ./scripts/package.sh

# Example site
.PHONY: ecweb
ecweb:
	.venv/bin/python3 -m recrawler.main ./examples/ecweb.yaml
