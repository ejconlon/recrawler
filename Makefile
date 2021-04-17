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
	python3 -m piptools compile

.PHONY: lint
lint:
	.venv/bin/flake8 *.py

.PHONY: typecheck
typecheck:
	.venv/bin/mypy *.py

# .PHONY: unit
# unit:
# 	.venv/bin/python -m pytest -v .

.PHONY: test
test: lint typecheck

.PHONY: package
package:
	rm -rf .build
	mkdir -p .build/recrawler
	python3 -m pip install -t .build/recrawler -r requirements.txt
	cp -r recrawler .build/recrawler/recrawler
	echo '#!/bin/bash\nset -eux\npython3 -m recrawler.main $$@\n' > .build/recrawler/main.sh
	chmod +x .build/recrawler/main.sh
