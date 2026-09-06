# Banking Analytics Workshop — one command per intention.
# `make setup` once, `make verify` any time you feel lost.

PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: setup verify data train-score train-adjudication price train-ews train-line-increase docpack test run stop notebooks reading

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

# The notebooks live on `main` only — they are a *view onto* whatever stage you are
# at, not part of any stage's contents (no tag contains them). So `git checkout
# stage-N` deletes them, which looks like they were lost. This brings them back
# without moving you off the stage. It refuses if you have unsaved notebook edits.
#
# NOTE this target only exists on `main`: a stage tag ships the Makefile it had at
# the time, and tags never move. After a stage jump the student-facing command is
# `git checkout main -- notebooks`, which needs nothing but git. That is what the
# lab sheets and CHECKPOINTS.md print; this target is the nicety for main.
notebooks:
	@git rev-parse --verify -q main >/dev/null || \
	  { echo "No 'main' branch here. Are you in a clone of the workshop repo?"; exit 1; }
	@git diff --quiet -- notebooks || \
	  { echo "You have unsaved edits in notebooks/ — this would overwrite them."; \
	    echo "Park them first:  git stash push -- notebooks"; exit 1; }
	@git checkout main -- notebooks
	@echo "notebooks/ restored from main. Open the one matching stage.txt ($$(cat stage.txt))."

# Post-session reading notes. The HTML is the source of truth; the PDF is committed
# next to it so students can just download it. You only need this target to re-render
# after editing the HTML. Any recent Chrome or Chromium will do.
CHROME := $(shell for p in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
	"/Applications/Chromium.app/Contents/MacOS/Chromium" \
	"$$(command -v google-chrome)" "$$(command -v chromium)"; do \
	  [ -n "$$p" ] && [ -x "$$p" ] && echo "$$p" && break; done)

reading:
	@[ -n "$(CHROME)" ] || { echo "No Chrome/Chromium found. The PDFs are committed, so you only need this to re-render."; exit 1; }
	@for f in workshop/reading/*.html; do \
	  "$(CHROME)" --headless --disable-gpu --no-pdf-header-footer \
	    --print-to-pdf="$${f%.html}.pdf" --virtual-time-budget=4000 \
	    "file://$(CURDIR)/$$f" >/dev/null 2>&1; \
	  echo "rendered $${f%.html}.pdf"; \
	done
