"use strict";
/* Pure renderers for the Early Warning tab, split from tab-ews.js from the
   start. Data in, DOM out, no network, no state. Uses el/fmt/debounce
   (util.js), svgEl/svgRoot/sparkline/divergingBars (svg.js) and
   axisWithHandles (axis-handles.js). Every number drawn here came straight
   off a server response -- nothing here decides a threshold or a tier.

   The plain-DOM tiles (tierChip/bookTierTiles/bookTriggerCounts/caveatBlock/
   driverBars) live in ews-tiles.js. */

const PANEL_SERIES = [
  {key: "utilization", label: "Utilization", format: v => fmt.pct(v, 0)},
  {key: "balance", label: "Balance", format: v => fmt.money(v)},
  {key: "deposit_inflow", label: "Deposit inflow", format: v => fmt.money(v)},
  {key: "days_past_due", label: "Days past due", format: v => fmt.num(v, 0)},
  {key: "overdraft_count", label: "Overdrafts", format: v => fmt.num(v, 0)},
];

/* smallMultiples -- five stacked sparklines over the account's real 24-month
   behaviour. Only utilization carries a threshold rule: HIGH_UTILIZATION's, read
   off the trigger row of the latest what-if response (never hardcoded), so it
   moves with a dragged slider. Final review I7: flag_triggers tests util_recent,
   the mean of the LAST 3 MONTHS, not the last month -- and on 1,689 of 8,336
   accounts the last month sat on the other side of the line from the verdict. The
   compared quantity is now drawn as its own bar over the last three months at the
   clause's server-given value, printed at the clause's dp, and the caption says
   what is tested and quotes the module's own verdict. */
function smallMultiples(panel, triggers) {
  const hu = (triggers || []).find(t => t.name === "HIGH_UTILIZATION");
  const c = hu ? hu.clauses[0] : null;
  const wrap = el("div", {class: "ews-panel"});
  for (const {key, label, format} of PANEL_SERIES) {
    const util = key === "utilization" && c !== null;
    wrap.append(sparkline(panel.series[key], {
      label, format, threshold: util ? c.threshold : null,
      marker: util ? {value: c.value, span: 3,
                      label: `3-mo mean ${fmt.pctAt(c.value, c.dp)}`} : null,
    }));
    if (util) {
      wrap.append(el("p", {class: "panel-axis muted"},
        `Dashed line: high_utilization ${fmt.pctAt(c.threshold, c.dp)}, tested against ` +
        `the 3-month mean (util_recent, the solid bar) ${fmt.pctAt(c.value, c.dp)}` +
        `${c.tied ? " — at the threshold" : ""} → ` +
        `${hu.fired ? "✗ HIGH_UTILIZATION fired" : "✓ HIGH_UTILIZATION not fired"}.`));
    }
  }
  wrap.append(el("p", {class: "panel-axis muted"},
    `month 0 … ${panel.months.length - 1}`));
  return wrap;
}

/* triggerTable -- one row per CLAUSE under a trigger group-header row, not one
   row per trigger. DELINQUENCY is a compound OR; on all 4,225 accounts where it
   fires, the SECOND clause (dpd_recent > 0) is true while the first
   (dpd_max >= 30) reads false -- one row, or the first clause alone, would
   print "value 2, threshold 30, FIRED": a row that contradicts itself on half
   the book. The header's fired glyph comes straight off the payload, never
   recomputed from a clause's `met`; `met` only explains which clause caused
   it. Same fired/passed/na convention as the decision tab's rulesTable.
   value/threshold format at the clause's own server-chosen `dp`
   (app/v2/display.py), not a fixed decimal count -- BIZ106189's util_drift
   0.15000000000000013 against a committed 0.15 both round to "0.15" at 4dp,
   so a FIRED row read "0.15 > 0.15". When `tied` (nothing up to 8dp
   separates them), the comparator column says so instead. met/fired stay
   the module's own verdict, unchanged. */
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
      const comparator = c.tied ? "at threshold" : c.comparator;
      body.append(el("tr", {}, el("td", {}, c.metric),
        el("td", {}, fmt.feature(c.value, c.dp)), el("td", {}, comparator),
        el("td", {}, fmt.feature(c.threshold, c.dp)),
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
   cutoffs. The pin is the UNROUNDED probability the tier was decided on, printed
   (with both handles) at the server's prob_dp -- the 4dp prob put BIZ108170's pin
   at "0.5073" beside "t_high 0.5073" under a Medium chip. Band edges are handle
   keys so the tiers move with the handles (final review I2). The axis never
   decides anything; it reports {t_med, t_high}, debounced 120ms. */
function tierBar(e, onChange) {
  return axisWithHandles({
    min: 0, max: 1, pin: e.prob_raw, pinLabel: "p(deterioration)",
    format: v => v.toFixed(e.prob_dp),
    bands: [{from: 0, to: "t_med", fill: "var(--ok)"},
            {from: "t_med", to: "t_high", fill: "var(--warn)"},
            {from: "t_high", to: 1, fill: "var(--bad)"}],
    handles: [{key: "t_med", value: e.tiers.t_med, label: "t_med"},
              {key: "t_high", value: e.tiers.t_high, label: "t_high"}],
  }, debounce(onChange, 120));
}
