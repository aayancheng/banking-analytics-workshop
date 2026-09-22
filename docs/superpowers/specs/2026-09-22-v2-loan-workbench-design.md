# v2 Loan Workbench — design

**Date:** 2026-09-22
**Status:** approved, ready for implementation planning
**Context:** Sessions 3 and 4 merge into one new Session 3 covering adjudication,
pricing & profitability, and early warning. Line increase becomes optional. The
portal gets a second, loan-level front end; the existing one stays untouched so the
two can be demonstrated side by side.

## Why

The v1 portal answers portfolio questions. A risk practitioner's actual unit of work
is one loan: *what did we decide, why, was it priced properly, and is it going bad?*
v1 can only answer the first of those per loan, and only shallowly.

v2 is also the session's set piece about agentic work: one prompt turned a read-only
summary page into a loan-level workbench. v1 must therefore survive verbatim for the
before/after.

## Non-goals

- Replacing or refactoring v1. `app/main.py` gains three lines and nothing else.
- Any new model, gate, or artifact. v2 reads what the modules already produce.
- A build step. No npm, no bundler, no CDN dependency (must work offline in a
  devcontainer / Codespace).
- Persisting anything. Slider state is per-session and in-memory only.

## The load-bearing constraint: no financial arithmetic in JavaScript

Every control posts its overrides to the server. The server calls **the same module
function the batch pipeline calls** and returns computed numbers. The browser renders
only.

| Control | Server calls |
|---|---|
| Rate / market sliders | `pricing.src.engine.price_loan` |
| PD cutoff pins | `adjudication.src.policy.decide` |
| EWS tier cutoffs | `ews.src.watchlist.risk_tier` |
| Trigger thresholds | `ews.src.triggers.flag_triggers` |
| LI amount rules | `line_increase.src.amount_rules.recommended_amount` / `incremental_roe` |

This is invariant 5 ("one service per module") made visible: the what-if and the
production run cannot drift because they are one function. A test asserts it —
**what-if at default settings must reproduce the batch pipeline's number exactly.**

Measured on this machine, so whole-book recompute on every drag is affordable:

| Operation | Rows | Time |
|---|---|---|
| `policy.decide` | 12,000 | 0.002s |
| `flag_triggers` | 8,336 | 0.001s |
| `price_loan` | 1 | ~1µs (8,336 ≈ 8ms) |
| `feature_contributions` (WoE x beta) | 1 | 0.002s |
| `TreeExplainer.shap_values` | 1 | 0.003s |

No client-side approximation is needed and none is permitted.

## Architecture

New router and static page inside the existing service, served at `/v2`.

```
app/
  main.py          # +3 lines: import router, include_router, mount /static/v2
  v2/
    __init__.py
    state.py       # V2State: explainer, panel, cached frames; built in lifespan
    loans.py       # filter + search over the applicant universe
    explain.py     # per-loan assembly for each tab (read path)
    whatif.py      # overrides -> module call -> recomputed numbers (write path)
    router.py      # APIRouter, all /api/v2/* endpoints
  static/v2/
    index.html
    app.js
    styles.css
```

Rejected alternatives:

- **Separate app on port 8101.** Total isolation, but two processes, two Makefile
  targets, doubled model loading (+7s), and a new port for `make stop` and the
  failure playbook. More live-demo surface, no teaching gain.
- **v2 replaces v1.** Cleanest code; destroys the before/after comparison.

### State

v1's cold boot is 7.4s (imports + lifespan). v2 adds roughly 0.15s: one
`shap.TreeExplainer` over the adjudication model (0.116s) and `panel.parquet`
(0.01s, 200,064 rows). Per-loan explanations are computed on demand at 2–3ms, so
nothing is precomputed across the population.

v2 reuses `app.state` (scores, decisions, profiles, priced, ews, li) rather than
recomputing. The v2 additions are built in the same lifespan hook, after v1's, and
are strictly additive — removing them leaves v1 working.

### Stage-tag behaviour

`app/v2/` lives on `main` only, like `notebooks/` and `workshop/`. Stage tags never
move (invariant 1). Consequences:

- `verify.py`'s `check_apps` gains a v2 block guarded by
  `if (ROOT / "app" / "v2").exists()`, so it exercises v2 on `main` and stays silent
  at every tag. The one promise holds unchanged at stage-0..stage-5.
- The S3 stage-jump command becomes `git checkout main -- app notebooks workshop`.
  This must be updated everywhere the two-part handoff is printed.

## API

All under `/api/v2`. Read endpoints are GET; what-if endpoints are POST with an
overrides body, and **an empty override body must return the batch pipeline's exact
numbers**.

| Endpoint | Purpose |
|---|---|
| `GET /api/v2/filters` | Distinct values + counts for every filter facet |
| `GET /api/v2/loans?...` | Filtered, capped, sorted match list + total count |
| `GET /api/v2/loan/{id}` | Header block: identity, terms, score, PD, decision, booked |
| `GET /api/v2/loan/{id}/decision` | Rules ledger, PD zones, WoE x beta ledger, SHAP |
| `GET /api/v2/loan/{id}/pricing` | Full waterfall (dollars + bps), rate ladder, verdict |
| `GET /api/v2/loan/{id}/ews` | 24-month panel series, prob, tier, triggers, SHAP, caveat |
| `GET /api/v2/loan/{id}/line-increase` | Binding cap, incremental waterfall, 4-clause eligibility |
| `POST /api/v2/loan/{id}/decision/whatif` | `{t_low, t_high, ...}` -> this loan + book mix |
| `POST /api/v2/loan/{id}/pricing/whatif` | `{quoted_rate, cost_of_funds, lgd, ...}` -> waterfall + book share-clearing |
| `POST /api/v2/loan/{id}/ews/whatif` | `{t_high, t_med, trigger thresholds}` -> tier, triggers, book tier counts |

Unbooked applicants return `null` (HTTP 200) for the pricing/EWS/LI payloads, not a
404 and not a 500 — matching `customer_360`'s existing honest-null behaviour. Unknown
IDs are 404.

## Screens

### Selector

A filter bar driving a dropdown. Facets: decision, score band, industry, region,
booked, EWS tier, mispriced, LI-eligible, plus a free-text ID box. Facets compose,
show a live match count, and populate the dropdown. The dropdown lists at most 200
matches sorted by `business_id`; the match count always reports the true total, so a
broad filter reads "200 of 3,214 shown" rather than silently truncating. Finding a demo
case live — *"mispriced D-band Retail on the High watchlist"* — is four clicks, so no
IDs need memorising on the night.

### Persistent header

Never scrolls away, identical on every tab: `business_id`, industry / region / entity
type / years in business, requested amount / term / purpose / collateral, business
score + band, model PD, decision chip, booked badge. Plus a link to the v1 portal for
the side-by-side.

### Tab 1 — Decision

- **PD zone ruler.** Horizontal axis with `t_low` (0.0955) and `t_high` (0.4943) as
  draggable pins and this loan's PD marked. Dragging flips this loan's zone *and*
  updates the book's Approve/Refer/Decline mix beside it.
- **Rules ledger.** Every hard knockout (dscr floor 1.0, public records cap 0, prior
  delinquencies cap 3, leverage cap 6.0) and every refer override (dscr refer band
  1.0–1.2, score floor 600, request/revenue cap 0.75) as a row: rule, threshold, this
  loan's value, fired or not.
- **Two rationales, side by side.** The scorecard's signed WoE x beta ledger over all
  15 features as a diverging bar — exact and additive — next to the LightGBM's SHAP
  over its 21 features. That the two disagree in places is the teaching point.
- **Nearest flip.** Which single threshold is closest to changing this decision.

### Tab 2 — Pricing & Profitability

- **Full waterfall**, every line the engine already returns — interest income, cost of
  funds, expected loss, operating cost, pre-tax, tax, net income, allocated equity,
  ROE, RAROC — shown in dollars *and* as bps on EAD.
- **Rate ladder.** Break-even, hurdle-clearing, recommended, and quoted on one axis
  with this loan's quoted rate pinned; shortfall in bps.
- **Sliders:** quoted rate, cost of funds, LGD, opex rate, capital ratio, tax rate,
  fee rate, ROE hurdle. Market sliders also recompute the book's share-clearing
  (8ms), so moving LGD visibly fails the portfolio against its hurdle.
- **Reset to book assumptions** returns every slider to `shared.config.MARKET`.

### Tab 3 — Early Warning

- **The 24-month panel** for this account as inline-SVG small multiples: utilization,
  balance, deposit inflow, days past due, overdraft count. This is the literal answer
  to "what happened to this loan", and it is real data the modules already aggregate.
- **p(deterioration)** with draggable `t_high` / `t_med` tier cutoffs.
- **Named triggers** (HIGH_UTILIZATION, RISING_UTILIZATION, DELINQUENCY,
  DEPOSIT_DECLINE, FREQUENT_OVERDRAFTS) with draggable thresholds and this account's
  value against each.
- **SHAP drivers** for the probability.
- **The caveat on screen, not in a footnote:** top-decile capture 0.2159 held out,
  AUC 0.6622 *reported, not gated*. Quoting the metadata number, per the house rule
  about held-out vs in-sample.

### Tab 4 — Line Increase (marked *optional module*)

Skippable live without leaving a hole in the layout.

- Which of the three caps binds: headroom to target utilization (0.65), percent cap
  (0.50 x limit), or revenue ceiling (0.30 x revenue − limit).
- The incremental waterfall from `incremental_roe`.
- **Eligibility as a four-clause AND**, each clause pass/fail: `prob >= 0.3121`,
  `pd <= 0.0741`, `amount > 0`, `clears_hurdle`. This puts the documented trap —
  95 eligible vs 1,243 with a positive recommended amount — on screen.

## Front end

No build step, no CDN. Hand-rolled inline SVG for the panel charts, the PD ruler, the
rate ladder and the diverging bars — the same stdlib-only spirit as
`workshop/slides/render_html.py`.

`localStorage` is wrapped in try/catch at every access or not used at all: it throws
rather than returning null in restricted contexts, and an unguarded access already
killed a handler once in `run-of-show-app.html`. Slider state is a convenience, never
a dependency.

Layout targets a projected screen on Zoom: large type, high contrast, no hover-only
information.

## Testing

`tests/test_app_v2.py`, FastAPI `TestClient`, in-process:

1. **What-if at defaults equals the batch pipeline.** For a fixed sample of 25 loans
   (five per score band, taken in `business_id` order so the set is deterministic), the
   pricing what-if with an empty override body reproduces `price_population`'s row
   exactly; the decision what-if with the committed `policy_config.json` reproduces
   the batch `decide` exactly. This is the invariant-5 test.
2. Filter endpoint counts match direct pandas filtering of the same frames.
3. An unbooked applicant returns 200 with null pricing/EWS/LI payloads.
4. An unknown `business_id` returns 404 on every loan endpoint.
5. Override validation: out-of-range values are rejected, not silently clamped into a
   number that looks real.

`verify.py`'s `check_apps` gains the guarded v2 smoke described above.

## Curriculum consequences (tracked, not done here)

- S3 handoff command changes to `git checkout main -- app notebooks workshop`.
- The S3 lab ships v2 with **Tab 3 (Early Warning)** stubbed; students prompt an
  agent to build it, with the original prompt as the worked example. Tab 3 is chosen
  because its data story is self-contained and the panel series is already available.
- The prompt that produced v2 is itself teaching material and should be preserved
  verbatim in the session's prompt cards.
