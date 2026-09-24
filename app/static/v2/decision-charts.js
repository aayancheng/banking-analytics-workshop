"use strict";
/* Pure renderers for the Decision tab, split from tab-decision.js on the same
   rendering-vs-orchestration seam as pricing-charts.js/ews-charts.js. Data in,
   DOM out, no network, no state. Uses el/fmt/debounce (util.js), divergingBars
   (svg.js) and axisWithHandles (axis-handles.js). Every fired/clear state, count
   and footer number comes straight from a server response -- nothing here
   compares a value to a threshold. */

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
    // value and threshold at the row's server-chosen dp (app/v2/display.py) --
    // String(value) could print a value a hair across its threshold as equal to it.
    const [v, t] = fmt.pair(r.value, r.threshold, r.dp);
    body.append(el("tr", {}, el("td", {}, r.label), el("td", {}, v),
      el("td", {}, r.tied ? "at threshold" : r.comparator), el("td", {}, t),
      el("td", {}, status)));
  }
  const t = el("table", {class: "rules"});
  t.append(el("caption", {}, caption), el("thead", {}, el("tr", {},
    el("th", {}, "rule"), el("th", {}, "this loan"), el("th", {}, "comparator"),
    el("th", {}, "threshold"), el("th", {}, "status"))), body);
  return t;
}

/* ledgerBars -- one additive rationale (divergingBars + a footer that reads the
   additive identity). The footer prints `ledger.display.{intercept,
   contributions_total, logit}` verbatim -- no arithmetic at all, not even a
   subtraction of two response numbers. Those three were briefly derived here as
   `logit_pd - intercept`: individually correct, but still a number invented in
   the browser and untraceable to the server, which is exactly what this project
   forbids (a drift nothing would catch). display_triple() in ledgers.py now does
   the rounding AND the reconciliation server-side (rounding intercept and
   log-odds independently to 4dp before subtracting -- rather than rounding a full-
   precision subtraction -- left the printed equation off by one in the last place
   on 30.5% of loans (score) / 17.5% (shap), measured), so the three fields already
   satisfy intercept + contributions_total == logit at `display.dp` decimals.
   `.toFixed(display.dp)` below is formatting a number that already IS the display
   value, not computing one. */
function ledgerBars(ledger, title, interceptLabel = "intercept") {
  const d = ledger.display;
  const wrap = el("div", {class: "ledger"});
  wrap.append(el("h3", {}, title), divergingBars(ledger.contributions));
  wrap.append(el("p", {class: "ledger-footer"},
    `${interceptLabel} ${d.intercept.toFixed(d.dp)} + contributions ` +
    `${d.contributions_total.toFixed(d.dp)} = log-odds ${d.logit.toFixed(d.dp)}`));
  return wrap;
}

/* pdRuler -- axisWithHandles configured for the PD zone cutoffs. The pin is the
   ADJUDICATION-model PD (decisions["pd"]), which is what the zones test -- not
   the scorecard PD the header shows; they differ by >1pp on 77% of applicants
   and fall in different zones on 2,338 of 12,000, so the label names which one.
   Band edges are handle keys, so the zones move with the handles (final review
   I2); pin and handles print at the server's pd_zones.dp, re-sent on every
   what-if via setFormat. The axis never decides anything. */
function pdRuler(z, onChange) {
  const top = Math.max(0.6, z.pd * 1.2);
  return axisWithHandles({
    min: 0, max: top, pin: z.pd, pinLabel: "adjudication-model PD",
    format: v => v.toFixed(z.dp),
    bands: [{from: 0, to: "t_low", fill: "var(--ok)"},
            {from: "t_low", to: "t_high", fill: "var(--warn)"},
            {from: "t_high", to: top, fill: "var(--bad)"}],
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

/* Rendered from every what-if response, not only the first GET (final review
   I6: after a drag it quoted the old cutoff). value/threshold at the server's dp
   -- a PD lever's value is the unrounded PD, which String() printed at 16 digits. */
function nearestFlipLine(nf) {
  if (!nf || !nf.lever) return el("p", {class: "muted"}, "No ranked lever.");
  const [v, t] = fmt.pair(nf.value, nf.threshold, nf.dp);
  return el("p", {class: "nearest-flip"},
    `Nearest flip: ${nf.label} — this loan ${v} ${nf.tied ? "at" : "vs"} threshold ` +
    `${t} (gap ${fmt.num(nf.gap, 4)}).`);
}

