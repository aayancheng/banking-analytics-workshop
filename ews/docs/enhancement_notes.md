# EWS — Enhancement Notes (for the model whitepaper agent)

**Status:** Documented, NOT executed. Picked up by the model-whitepaper / documentation
agent as a known limitation + a concrete future enhancement.

## Known limitation (current build — Option B)

The Module 3 Early-Warning model is gated and reported honestly against a **noise-capped
synthetic target**. The `deterioration_next_6_12mo` label in `shared/data_generator.py`
(lines ~138–146) is generated as:

```
det_logit = -2.4 + 3.0·pd_true
                 + 2.0·max(util_last3 − 0.85, 0)
                 + 1.5·max(util_trend, 0)
                 + 0.4·z(leverage)
                 + N(0, 0.4)            # large logit noise
deterioration = Bernoulli( sigmoid(det_logit) )   # + irreducible coin-flip noise
```

Two compounding noise sources (the `N(0, 0.4)` logit noise and the Bernoulli draw) put a
hard ceiling on learnable signal:

- **Oracle test** (model fed ground-truth `pd_default_origination` + exact DGP inputs):
  **AUC ≈ 0.704** — the theoretical maximum for *any* model on this data.
- **Shipped model** (leakage-safe features): **AUC 0.662, PR-AUC 0.308 (base 0.180),
  top-decile capture 21.6% = 2.16× lift.**

Because AUC ≥ 0.75 and top-decile capture ≥ 3× are unreachable on this data, the build gates
on what the data genuinely supports: **top-decile capture ≥ 2× lift** and **PR-AUC > base
rate**, with AUC reported (not gated). This is a deliberate, documented demo choice — see the
"Gate note" in `ews/docs/validation_report.md`.

## Option A — signal-sharpening enhancement (deferred; do NOT run now)

To lift the model into the master-spec target (top-decile capture ≥ 3×, AUC ≥ 0.75) for a
production-grade demo, sharpen the synthetic deterioration signal in
`shared/data_generator.py`:

1. Reduce the deterioration logit noise: `rng.normal(0, 0.4, m)` → `rng.normal(0, 0.18, m)`
   (line ~144). (Leave the line-increase noise on line ~154 unchanged.)
2. Optionally raise the behavioral coefficients (e.g. the `2.0·max(util_last3−0.85,0)` and
   `1.5·max(util_trend,0)` terms) so the panel-trend features carry more signal.
3. Regenerate: `./.venv/bin/python -m shared.data_generator`.
4. Restore the stronger EWS gate in `ews/src/train.py`: `CAPTURE_GATE = 0.30` and re-add an
   `AUC_GATE = 0.75` assertion (and the matching `test_model.py` assertions).
5. Retrain: `./.venv/bin/python -m ews.src.train` → expect AUC ≥ 0.75, capture ≥ 3×.

**Safety analysis (verified):** scaling a single `rng.normal(...)` draw of the same shape
does not change the random-number stream that follows it, and `businesses.parquet` is
generated entirely before the portfolio/panel step. Therefore Option A changes **only** the
`deterioration_next_6_12mo` label (and the not-yet-built `line_increase_good`, which depends
on it). The Score, Adjudication, and Pricing modules read `businesses.parquet` + the panel +
unrelated portfolio columns and are **unaffected** — confirm by checksumming
`businesses.parquet` before/after regeneration. Their gates (Score AUC 0.82, Adjudication AUC
0.81, Pricing engine) should reproduce unchanged.

**Why deferred:** this is a prototype demonstrating speed-to-market with synthetic data, not a
production model. Option B keeps the already-merged data foundation untouched and reports the
EWS performance honestly. Option A is the path to a stronger early-warning story when desired.
