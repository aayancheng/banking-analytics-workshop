# Banking Analytics Workshop — one command per intention.
# `make setup` once, `make verify` any time you feel lost.

PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: setup verify data train-score train-adjudication price train-ews train-line-increase docpack test run stop

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

verify:
	$(PY) verify.py

data:
	$(PY) -m shared.data_generator
	$(PY) -m shared.data_quality

train-score:
	$(PY) -m score.src.train

train-adjudication:
	$(PY) -m adjudication.src.train

price:
	$(PY) -m pricing.src.portfolio

train-ews:
	$(PY) -m ews.src.train

train-line-increase:
	$(PY) -m line_increase.src.train

docpack:
	$(PY) -m tools.build_doc_pack

test:
	$(PY) -m pytest -q tests

# Depends on stop: a leftover uvicorn on 8100 makes `make run` die with
# "address already in use" — which is exactly what happens when you re-run it during
# a demo. Freeing the port first is always what you meant.
run: stop
	$(PY) -m uvicorn app.main:app --port 8100

stop:
	-@lsof -ti :8100 | xargs kill 2>/dev/null || true
	-@lsof -ti :5180 | xargs kill 2>/dev/null || true
	@echo "Workshop ports (8100, 5180) are free."
