"use strict";
/* Task 12 -- Decision tab: the policy ledger, both model rationales, and a
   draggable PD ruler that re-decides the whole book server-side on every drag.
   Uses api/fmt/el/debounce (util.js) and divergingBars/axisWithHandles
   (svg.js/axis-handles.js). This file formats and draws; every fired/clear state,
   every book-mix count, and the additive-footer numbers come straight from a
   server response -- nothing here compares a value to a threshold. */

/* rulesTable -- the three-state ledger. Never paints a non-applicable row red: on
   43.4% of applicants a refer override's condition is true while it changed
   nothing (BIZ100052 -- v1 reports "rule hits: none"), so colour is never the sole
   carrier of meaning and a true-but-inert condition gets a quiet parenthetical
   instead of a false alarm. */
function rulesTable(rows, caption) {
  const body = el("tbody");
  for (const r of rows) {
    let status;
    if (r.fired) {
      status = el("span", {class: "fired"}, "✗ fired");
    } else if (r.applicable) {
      status = el("span", {class: "passed"}, "✓ clear");
    } else {
      const note = r.condition_met
        ? " (condition true, but the PD zones already decided)" : "";
      status = el("span", {class: "na"}, "— n/a" + note);
    }
    body.append(el("tr", {}, el("td", {}, r.label), el("td", {}, String(r.value)),
      el("td", {}, r.comparator), el("td", {}, String(r.threshold)),
      el("td", {}, status)));
  }
  const t = el("table", {class: "rules"});
  t.append(el("caption", {}, caption), el("thead", {}, el("tr", {},
    el("th", {}, "rule"), el("th", {}, "this loan"), el("th", {}, "comparator"),
    el("th", {}, "threshold"), el("th", {}, "status"))), body);
  return t;
}

/* ledgerBars -- one additive rationale (divergingBars + a footer that reads the
   additive identity). The response carries the intercept/base value and the
   resulting log-odds but never a running total of `contributions`: looping over
   that array in JS would re-derive a number the server already computed (and risk
   drifting from it on 15-21 float additions). The middle term is instead the one
   subtraction of two numbers the response already gives -- the identity
   score_ledger/shap_ledger assert server-side (to 1e-9 / 1e-6), never a sum over
   per-feature values performed here.
   Rounding is a display concern the ledger modules explicitly hand to the browser
   (see ledgers.py). Rounding intercept and log-odds to 4dp *independently* and
   then subtracting the unrounded pair for the middle term prints an equation that
   is off by 1 in the last place (e.g. -1.6217 + -0.8344 = -2.4562 on screen): a
   room checking the sum by eye would read that as a bug. Deriving the middle term
   from the two already-rounded numbers makes the printed equation exactly
   self-consistent, still without summing a single `contributions` row. */
function ledgerBars(ledger, title, interceptLabel = "intercept") {
  const intercept = Number((ledger.intercept ?? ledger.base_value).toFixed(4));
  const logOdds = Number((ledger.logit_pd ?? ledger.logit_pd_model).toFixed(4));
  const wrap = el("div", {class: "ledger"});
  wrap.append(el("h3", {}, title), divergingBars(ledger.contributions));
  wrap.append(el("p", {class: "ledger-footer"},
    `${interceptLabel} ${intercept.toFixed(4)} + contributions ` +
    `${(logOdds - intercept).toFixed(4)} = log-odds ${logOdds.toFixed(4)}`));
  return wrap;
}

/* pdRuler -- axisWithHandles configured for the PD zone cutoffs, verbatim from the
   brief. The axis never decides anything; it reports {t_low, t_high} and the
   caller re-decides the whole book server-side, debounced 120ms. */
function pdRuler(z, onChange) {
  return axisWithHandles({
    min: 0, max: Math.max(0.6, z.pd * 1.2), pin: z.pd, pinLabel: "this loan PD",
    bands: [{from: 0, to: z.t_low, fill: "var(--ok)"},
            {from: z.t_low, to: z.t_high, fill: "var(--warn)"},
            {from: z.t_high, to: Math.max(0.6, z.pd * 1.2), fill: "var(--bad)"}],
    handles: [{key: "t_low", value: z.t_low, label: "t_low"},
              {key: "t_high", value: z.t_high, label: "t_high"}],
  }, debounce(onChange, 120));
}

/* book_mix omits a decision with zero count (pandas value_counts drops it), so a
   missing key means 0, not "unknown" -- never leave a tile blank. */
function bookMixTiles(mix, flippedCount) {
  const wrap = el("div", {class: "book-mix"});
  for (const k of ["Approve", "Refer", "Decline"]) {
    wrap.append(el("div", {class: "tile chip " + k},
      el("div", {class: "n"}, String(mix[k] ?? 0)), el("div", {class: "k"}, k)));
  }
  const box = el("div");
  box.append(wrap, el("p", {class: "flipcount"}, `${flippedCount} loans change decision`));
  return box;
}

function nearestFlipLine(nf) {
  if (!nf || !nf.lever) return el("p", {class: "muted"}, "No ranked lever.");
  return el("p", {class: "nearest-flip"},
    `Nearest flip: ${nf.label} — this loan ${String(nf.value)} vs threshold ` +
    `${String(nf.threshold)} (gap ${fmt.num(nf.gap, 4)}).`);
}

/* api() (util.js) discards the response body on a non-2xx status, but an
   out-of-range or inverted drag must surface the server's own 422 message, not a
   bare status code or a silent failure. A local fetch that always reads the body
   keeps that message intact without touching the shared helper every other tab
   also uses. FastAPI's own field-range 422s carry a list of error objects;
   InvalidOverride (t_low > t_high, an inverted band) carries a plain string --
   handle both. */
async function postWhatif(id, body) {
  const r = await fetch(`/api/v2/loan/${id}/decision/whatif`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = Array.isArray(data.detail)
      ? data.detail.map(e => e.msg).join("; ") : (data.detail || `request failed (${r.status})`);
    throw new Error(msg);
  }
  return data;
}

TABS.decision = async (panel, id) => {
  const d = await api(`/api/v2/loan/${id}/decision`);
  const seed = await postWhatif(id, {});  // empty overrides == the batch pipeline

  panel.innerHTML = "";
  const topBox = el("div", {id: "dec-top"});
  const err = el("p", {class: "dec-error hidden"});
  const rulerBox = el("div", {class: "dec-ruler"});
  const tables = el("div", {id: "dec-tables"});
  panel.append(topBox, err, rulerBox, tables,
    ledgerBars(d.score_ledger, "Scorecard rationale (WoE × β)"),
    ledgerBars(d.shap, "Adjudication model rationale (SHAP)", "base value"),
    nearestFlipLine(d.nearest_flip));

  // Only these two containers are ever rebuilt after the initial draw -- the ruler
  // SVG (and the pointer capture a live drag holds on it) is never touched, which
  // is what keeps a drag-triggered re-render from detaching the node mid-drag.
  const paint = w => {
    topBox.innerHTML = "";
    topBox.append(el("span", {class: "chip " + w.decision}, w.decision),
                  bookMixTiles(w.book_mix, w.flipped_count));
    tables.innerHTML = "";
    tables.append(rulesTable(w.rules.knockouts, "Knockout rules"),
                  rulesTable(w.rules.refer_overrides, "Refer overrides"));
  };
  paint(seed);

  rulerBox.append(pdRuler(d.pd_zones, async vals => {
    try {
      const w = await postWhatif(id, vals);
      err.classList.add("hidden");
      paint(w);
    } catch (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    }
  }));
};
