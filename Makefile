.PHONY: error
error:
	exit 1

.PHONY: venv
venv:
	rm -rf .venv
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

.PHONY: pipcompile
pipcompile:
	python3 -m piptools compile requirements.in
	python3 -m piptools compile dev-requirements.in

.PHONY: lint
lint:
	.venv/bin/flake8 recrawler/*.py

.PHONY: typecheck
typecheck:
	.venv/bin/mypy recrawler/*.py

# .PHONY: unit
# unit:
# 	.venv/bin/python -m pytest -v .

.PHONY: test
test: lint typecheck

.PHONY: package
package:
	./scripts/package.sh

.PHONY: docker-build
docker-build:
	cd docker && docker build -t recrawler-build .

.PHONY: docker-package
docker-package: docker-build
	docker run -it -v ${PWD}:/project -w /project recrawler-build /bin/bash ./scripts/package.sh

.PHONY: ecweb
ecweb:
	.venv/bin/python3 -m recrawler.main ../ecweb/recrawler.yaml
