"use strict";
/* Pure renderers for the Early Warning tab, split from tab-ews.js from the
   start. Data in, DOM out, no network, no state. Uses el/fmt/debounce
   (util.js), svgEl/svgRoot/sparkline/divergingBars (svg.js) and
   axisWithHandles (axis-handles.js). Every number drawn here came straight
   off a server response -- nothing here decides a threshold or a tier.

   Fix round 1: tierChip/bookTierTiles/bookTriggerCounts/caveatBlock/
   driverBars moved here from tab-ews.js to stay under the line budget --
   plain-DOM tile builders belong beside the SVG renderers, the split
   pricing-charts.js already uses for verdictTiles/bookStrip. */

const TIER_GLYPH = {Low: "✓", Medium: "!", High: "✗"};
// Same order ews.py's _TRIGGER_SPECS uses.
const TRIGGER_NAMES = ["HIGH_UTILIZATION", "RISING_UTILIZATION", "DELINQUENCY",
                       "DEPOSIT_DECLINE", "FREQUENT_OVERDRAFTS"];

const PANEL_SERIES = [
  {key: "utilization", label: "Utilization", format: v => fmt.pct(v, 0)},
  {key: "balance", label: "Balance", format: v => fmt.money(v)},
  {key: "deposit_inflow", label: "Deposit inflow", format: v => fmt.money(v)},
  {key: "days_past_due", label: "Days past due", format: v => fmt.num(v, 0)},
  {key: "overdraft_count", label: "Overdrafts", format: v => fmt.num(v, 0)},
];

/* smallMultiples -- five stacked sparklines over the account's real 24-month
   behaviour. Only utilization carries a threshold rule: HIGH_UTILIZATION's
   cutoff, read off triggerConfig (a what-if response's `trigger_config`, never
   hardcoded) so the dashed line agrees with the trigger table. Fix round 1:
   this used to read the GET's triggers array once and never refresh -- the
   caller now re-renders this block on every paint() with the latest
   trigger_config, so dragging high_utilization moves the line with it. One
   caption labels the shared x-axis once, instead of five times. */
function smallMultiples(panel, triggerConfig) {
  const threshold = triggerConfig ? triggerConfig.high_utilization : null;
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

// Colour is never the sole carrier of a tier state -- every chip/tile below
// carries TIER_GLYPH alongside the colour class.
function tierChip(tier) {
  return el("span", {class: "chip " + tier}, `${TIER_GLYPH[tier] ?? ""} ${tier}`);
}

// book_tiers can omit a tier with zero accounts (pandas value_counts drops it --
// the same trap tab-decision.js's bookMixTiles guards for decisions).
function bookTierTiles(counts) {
  const wrap = el("div", {class: "book-mix"});
  for (const k of ["Low", "Medium", "High"]) {
    wrap.append(el("div", {class: "tile chip " + k},
      el("div", {class: "n"}, String(counts[k] ?? 0)),
      el("div", {class: "k"}, `${TIER_GLYPH[k]} ${k}`)));
  }
  return wrap;
}

// The whole book's fired count per trigger -- the visible payoff of dragging a
// trigger threshold (high_utilization 0.90 -> 0.10 takes this from 628 to
// ~7,538), the same role bookTierTiles plays for the tier bar.
function bookTriggerCounts(counts) {
  const wrap = el("div", {class: "trigger-counts"});
  for (const name of TRIGGER_NAMES) {
    wrap.append(el("span", {class: "trigger-count"},
      `${name.replace(/_/g, " ")} ${counts[name] ?? 0}`));
  }
  return wrap;
}

// The model's limits as visible body text next to its own output, quoted
// verbatim from model_caveat -- never recomputed, and left in the metadata's
// own decimal units (not a percent) so the figures match metadata.json exactly.
function caveatBlock(c) {
  const wrap = el("div", {class: "ews-caveat"});
  wrap.append(
    el("p", {},
      `Top-decile capture ${fmt.num(c.top_decile_capture, 4)} held out ` +
      `(lift ${fmt.num(c.top_decile_lift, 4)}×). AUC ${fmt.num(c.auc, 4)} — ` +
      `reported, not gated. Base rate ${fmt.num(c.base_rate, 4)}.`),
    el("p", {}, c.note));
  return wrap;
}

// SHAP drivers are adverse-only (top_adverse_shap keeps positive contributions
// only), so divergingBars always renders them pushing one direction -- reused
// as-is. No feature "value" here (unlike the decision tab's ledgers), so
// fmt.feature(undefined) prints blank in that slot: display-only.
function driverBars(drivers) {
  if (!drivers.length) return el("p", {class: "muted"}, "No adverse SHAP drivers.");
  return divergingBars(drivers.map(d => ({feature: d.feature, contribution: d.impact})));
}
