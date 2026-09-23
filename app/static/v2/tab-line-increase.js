"use strict";
/* Task 15 -- Line Increase tab: read-only (no what-if endpoint exists for this
   module), so orchestration and rendering both live here rather than splitting
   across a *-charts.js file. Uses api/fmt/el (util.js) and hbars (svg.js) and
   waterfallTable (pricing-charts.js, loaded before this file -- its incremental
   lines share the exact eight `line` keys pricing's waterfall uses, both coming
   from pricing.src.engine.profit_waterfall).

   This module is optional in the curriculum: skippable live without leaving a
   hole, hence the ribbon. Its whole point is the documented gap between
   `eligible` (95 accounts, the authority) and `recommended_amount > 0` (1,243) --
   rendering the four ANDed clauses that make up `eligible` is what makes that
   gap visible instead of a footnote. Every number on screen is quoted straight
   off the response; nothing here computes a financial figure. */

// prob_above_threshold and pd_within_appetite are plain probability/PD figures --
// formatted via fmt.feature at the clause's own server-chosen `dp`
// (app/v2/display.py), not a hardcoded decimal count. A fixed 6dp (Task 15's first
// draft, for the documented BIZ101719 near-miss) was only 3.3x from colliding on
// this data; the server now measures the real margin per clause, per loan.
// amount_positive and clears_hurdle keep their own units (dollars, a rate) since
// dp doesn't apply to them the same way -- `tied` still governs their comparator
// text below.
const CLAUSE_FMT = {
  amount_positive: v => fmt.money(v),
  clears_hurdle: v => fmt.pct(v, 2),
};

function capsChart(caps) {
  const wrap = el("div", {class: "li-caps"});
  if (!caps.length) {
    wrap.append(el("p", {class: "muted"},
      "This account carries no credit limit, so there are no amount caps to compare."));
    return wrap;
  }
  const binding = caps.find(c => c.binding);
  wrap.append(hbars(caps), el("p", {class: "li-caption"},
    `The binding cap is ${binding.name.replace(/_/g, " ")}, at ${fmt.money(binding.amount)}.`));
  return wrap;
}

// The four clauses, in candidates()'s own AND order, each with its own pass/fail
// -- rendered faithfully, never recomputed. The footer's verdict is
// `eligibility.eligible` itself: `eligible == all(clause.pass)` is necessary but
// not sufficient (a wrong clause can still land on the right verdict), so the
// footer never derives yes/no from the rows above it. When `c.tied` (server-side,
// app/v2/display.py), the comparator column says the value is at the threshold
// instead of repeating a symbol that would print two equal numbers -- e.g.
// BIZ101719's amount_positive, $0 against a $0 threshold, exactly.
function clauseList(eligibility) {
  const body = el("tbody");
  for (const c of eligibility.clauses) {
    const format = CLAUSE_FMT[c.name] || (v => fmt.feature(v, c.dp));
    const comparator = c.tied ? "at threshold" : c.comparator;
    const glyph = c.pass ? "✓ pass" : "✗ fail";
    body.append(el("tr", {}, el("td", {}, c.name.replace(/_/g, " ")),
      el("td", {}, format(c.value)), el("td", {}, comparator),
      el("td", {}, format(c.threshold)),
      el("td", {}, el("span", {class: c.pass ? "passed" : "fired"}, glyph))));
  }
  const t = el("table", {class: "rules"});
  t.append(el("caption", {}, "Eligibility clauses"), el("thead", {}, el("tr", {},
    el("th", {}, "clause"), el("th", {}, "this loan"), el("th", {}, "comparator"),
    el("th", {}, "threshold"), el("th", {}, "status"))), body);
  const names = eligibility.clauses.map(c => c.name.replace(/_/g, " "));
  const wrap = el("div");
  wrap.append(t, el("p", {class: "li-verdict"},
    `eligible = ${names.join(" AND ")} → ${eligibility.eligible ? "✓ yes" : "✗ no"}`));
  return wrap;
}

// An empty waterfall (no increase recommended, incremental EAD 0) is a real
// state, said in words rather than drawn as an empty table.
function incrementalWaterfallBox(incremental) {
  const wrap = el("div");
  if (!incremental.waterfall.length) {
    wrap.append(el("p", {class: "muted"},
      "No increase is recommended, so there is no incremental exposure to price."));
    return wrap;
  }
  wrap.append(waterfallTable(incremental.waterfall, incremental.ead, "Incremental waterfall"));
  wrap.append(el("p", {class: "li-caption"},
    `Incremental ROE ${fmt.pct(incremental.roe, 2)} does not change with the EAD ` +
    `scale above -- ROE is EAD-invariant. ` +
    `${incremental.clears_hurdle ? "✓ clears" : "✗ short of"} the hurdle.`));
  return wrap;
}

function cohortStrip(cohort) {
  const mk = (label, node) => {
    const d = el("div", {class: "tile"});
    d.append(el("div", {class: "n"}, node), el("div", {class: "k"}, label));
    return d;
  };
  const wrap = el("div", {class: "li-cohort"});
  wrap.append(mk("Offered", cohort.n_offered.toLocaleString()),
    mk("Cohort PD", fmt.pct(cohort.cohort_pd, 2)), mk("Book PD", fmt.pct(cohort.book_pd, 2)),
    mk("Aggregate incremental ROE", fmt.pct(cohort.agg_incremental_roe, 2)),
    mk("ROE hurdle", fmt.pct(cohort.roe_hurdle, 2)));
  return wrap;
}

TABS.line_increase = async (panel, id) => {
  const li = await api(`/api/v2/loan/${id}/line-increase`);
  panel.innerHTML = "";
  panel.append(el("p", {class: "li-ribbon"},
    "Optional module — line increase is skippable live without leaving a hole."));
  if (li === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is no line to increase."));
    return;
  }
  panel.append(
    el("h3", {}, "Amount caps"), capsChart(li.caps),
    el("h3", {}, "Eligibility"), clauseList(li.eligibility),
    el("h3", {}, "Incremental economics"), incrementalWaterfallBox(li.incremental),
    el("h3", {}, "Offered cohort vs book"), cohortStrip(li.cohort));
};
