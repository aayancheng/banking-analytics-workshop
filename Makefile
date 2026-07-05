# Banking Analytics Workshop — one command per intention.
# `make setup` once, `make verify` any time you feel lost.

PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: setup verify data run stop

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

verify:
	$(PY) verify.py

data:
	$(PY) -m shared.data_generator
	$(PY) -m shared.data_quality

run:
	@echo "The apps arrive with stage-3. Until then: make verify."

stop:
	-@lsof -ti :8100 | xargs kill 2>/dev/null || true
	-@lsof -ti :5180 | xargs kill 2>/dev/null || true
	@echo "Workshop ports (8100, 5180) are free."
