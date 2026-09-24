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
// amount_positive stays fmt.money -- safe by construction, amounts move in $1,000
// steps. clears_hurdle is a fraction shown as a percent, so a FIXED 2dp-of-percent
// silently discarded the server's `dp` (fix round 3): BIZ103012's incremental ROE
// 0.14997213 against a 0.15 hurdle gets dp=5 from the server (a real, untied
// separation) but rendered "15.00% >= 15.00% -- FAIL", the same self-contradiction
// class as an EWS float-noise row, just introduced back in by the browser this
// time. A fraction needs (dp - 2) percent decimals to carry the same precision as
// dp decimals of the fraction; Math.max(2, ...) keeps the floor at today's 2dp so
// a comfortably-separated loan (the common case, dp = base_dp = 4) still prints
// plain "16.69%", not needless digits.
const CLAUSE_FMT = {
  amount_positive: v => fmt.money(v),
  clears_hurdle: (v, dp) => fmt.pctAt(v, dp),
};

/* The caps, then the steps recommended_amount() takes from the lowest of them --
   all from the server's amount_steps (final review I4). The caption used to say
   "the binding cap is X, at $-12,345" on 7,069 accounts and "$14,554" beside a
   $15,000 recommendation on 579 (BIZ100084), because the module floors at 0 and
   rounds to $1,000 AFTER taking the min. Every amount below is quoted from the
   payload; the words name each step so they never contradict the bars. */
function capsChart(caps, steps) {
  const wrap = el("div", {class: "li-caps"});
  if (!caps.length) {
    wrap.append(el("p", {class: "muted"},
      "This account carries no credit limit, so there are no amount caps to compare."));
    return wrap;
  }
  const name = steps.binding.replace(/_/g, " ");
  const words = steps.no_headroom
    ? `No headroom: the lowest cap, ${name}, is ${fmt.money(steps.min_cap)} — at or ` +
      `below zero, so the increase floors at $0 → recommended ` +
      `${fmt.money(steps.recommended)}.`
    : `Lowest cap: ${name}, ${fmt.money(steps.min_cap)} → floored at $0: ` +
      `${fmt.money(steps.floored_at_zero)} → rounded to the nearest ` +
      `${fmt.money(steps.round_to)}` +
      (steps.half_to_even ? " (an exact half rounds to the even multiple)" : "") +
      ` → recommended ${fmt.money(steps.recommended)}.`;
  wrap.append(hbars(caps), el("p", {class: "li-caption"}, words));
  return wrap;
}

// The four clauses, in candidates()'s own AND order, each with its own pass/fail
// -- rendered faithfully, never recomputed. The footer's verdict is
// `eligibility.eligible` itself: `eligible == all(clause.pass)` is necessary but
// not sufficient (a wrong clause can still land on the right verdict), so the
// footer never derives yes/no from the rows above it. When `c.tied` (server-side,
// app/v2/display.py: the values differ, but only by float noise nothing up to 8dp
// separates), the comparator column says the value is at the threshold instead of
// repeating a symbol that would print two equal numbers. An EXACT match -- e.g.
// BIZ101719's amount_positive, $0 against a $0 threshold -- is not tied (fix
// round 2): "$0 > $0 ✗ fail" already reads correctly.
function clauseList(eligibility) {
  const body = el("tbody");
  for (const c of eligibility.clauses) {
    const format = CLAUSE_FMT[c.name] || (v => fmt.feature(v, c.dp));
    const comparator = c.tied ? "at threshold" : c.comparator;
    const glyph = c.pass ? "✓ pass" : "✗ fail";
    body.append(el("tr", {}, el("td", {}, c.name.replace(/_/g, " ")),
      el("td", {}, format(c.value, c.dp)), el("td", {}, comparator),
      el("td", {}, format(c.threshold, c.dp)),
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
  // ROE and hurdle both at the server's dp (final review I3): BIZ103012's
  // 0.14997 printed "15.00% ... ✗ short of the hurdle" beside a 15.00% hurdle.
  const d = incremental.dp;
  wrap.append(el("p", {class: "li-caption"},
    `Incremental ROE ${fmt.pctAt(incremental.roe, d)} against a ` +
    `${fmt.pctAt(incremental.roe_hurdle, d)} hurdle — ` +
    `${incremental.clears_hurdle ? "✓ clears" : "✗ short of"} the hurdle. ` +
    `It does not change with the EAD scale above: ROE is EAD-invariant.`));
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

TABS.line_increase = async (panel, id, fresh) => {
  const li = await api(`/api/v2/loan/${id}/line-increase`);
  if (!fresh()) return;   // another loan or tab was chosen while this loaded
  panel.innerHTML = "";
  panel.append(el("p", {class: "li-ribbon"},
    "Optional module — line increase is skippable live without leaving a hole."));
  if (li === null) {
    panel.append(el("p", {class: "muted"},
      "This applicant was never funded, so there is no line to increase."));
    return;
  }
  panel.append(
    el("h3", {}, "Amount caps"), capsChart(li.caps, li.amount_steps),
    el("h3", {}, "Eligibility"), clauseList(li.eligibility),
    el("h3", {}, "Incremental economics"), incrementalWaterfallBox(li.incremental),
    el("h3", {}, "Offered cohort vs book"), cohortStrip(li.cohort));
};
