"use strict";
/* Task 14 -- pure renderers for the Early Warning tab, split from tab-ews.js from
   the start (Task 13's tab-pricing.js needed a post-hoc split after it overflowed
   150 lines; this task does the split up front). Data in, DOM out, no network, no
   state. Uses el/fmt/debounce (util.js), svgEl/svgRoot/sparkline (svg.js) and
   axisWithHandles (axis-handles.js). Every number drawn here came straight off a
   server response -- nothing here decides a threshold or a tier. */

const PANEL_SERIES = [
  {key: "utilization", label: "Utilization", format: v => fmt.pct(v, 0)},
  {key: "balance", label: "Balance", format: v => fmt.money(v)},
  {key: "deposit_inflow", label: "Deposit inflow", format: v => fmt.money(v)},
  {key: "days_past_due", label: "Days past due", format: v => fmt.num(v, 0)},
  {key: "overdraft_count", label: "Overdrafts", format: v => fmt.num(v, 0)},
];

/* smallMultiples -- five stacked sparklines over the account's real 24-month
   behaviour (sparkline is svg.js's, used directly per the brief). Only
   utilization carries a threshold rule: HIGH_UTILIZATION's own committed cutoff,
   read off the triggers payload rather than hardcoded, so the dashed line always
   agrees with what the trigger table calls a fire. One caption labels the shared
   x-axis once, instead of five times. */
function smallMultiples(panel, triggers) {
  const hu = triggers.find(t => t.name === "HIGH_UTILIZATION");
  const threshold = hu ? hu.clauses[0].threshold : null;
  const wrap = el("div", {class: "ews-panel"});
  for (const {key, label, format} of PANEL_SERIES) {
    wrap.append(sparkline(panel.series[key], {
      label, format, threshold: key === "utilization" ? threshold : null,
    }));
  }
  wrap.append(el("p", {class: "panel-axis muted"},
    `month 0 … ${panel.months.length - 1}`));
  return wrap;
}

/* triggerTable -- one row per CLAUSE under a trigger group-header row, not one
   row per trigger. DELINQUENCY is a compound OR, and on all 4,225 accounts where
   it fires, the SECOND clause (dpd_recent > 0) is the one that is true while the
   first (dpd_max >= 30) reads false -- collapsing to one row, or showing only the
   first clause, would print "value 2, threshold 30, FIRED": a row that
   contradicts itself on half the book. The group header's fired glyph comes
   straight off the payload and is never recomputed from a clause's `met`; `met`
   only explains which clause caused it. Same fired/passed/na glyph convention as
   the decision tab's rulesTable. */
function triggerTable(rows) {
  const body = el("tbody");
  for (const t of rows) {
    const glyph = t.fired ? "✗" : "✓";
    body.append(el("tr", {class: "trig-group"}, el("td", {colspan: "5"},
      el("span", {class: t.fired ? "fired" : "passed"}, `${glyph} ${t.name}`),
      t.clauses.length > 1 ? ` — any of (${t.join})` : "")));
    for (const c of t.clauses) {
      const status = c.met ? el("span", {class: "fired"}, "✗ met")
                            : el("span", {class: "na"}, "— not met");
      body.append(el("tr", {}, el("td", {}, c.metric), el("td", {}, String(c.value)),
        el("td", {}, c.comparator), el("td", {}, String(c.threshold)),
        el("td", {}, status)));
    }
  }
  const tbl = el("table", {class: "rules"});
  tbl.append(el("caption", {}, "Behavioural triggers"), el("thead", {}, el("tr", {},
    el("th", {}, "metric"), el("th", {}, "this account"), el("th", {}, "comparator"),
    el("th", {}, "threshold"), el("th", {}, "status"))), body);
  return tbl;
}

/* tierBar -- axisWithHandles configured for the deterioration-probability tier
   cutoffs, verbatim from the brief. The axis never decides anything; it reports
   {t_med, t_high} and the caller re-tiers and re-flags the whole book
   server-side, debounced 120ms. */
function tierBar(prob, tiers, onChange) {
  return axisWithHandles({
    min: 0, max: 1, pin: prob, pinLabel: "p(deterioration)",
    bands: [{from: 0, to: tiers.t_med, fill: "var(--ok)"},
            {from: tiers.t_med, to: tiers.t_high, fill: "var(--warn)"},
            {from: tiers.t_high, to: 1, fill: "var(--bad)"}],
    handles: [{key: "t_med", value: tiers.t_med, label: "t_med"},
              {key: "t_high", value: tiers.t_high, label: "t_high"}],
  }, debounce(onChange, 120));
}
