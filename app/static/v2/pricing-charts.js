"use strict";
/* Task 13 fix round 1 -- split out of tab-pricing.js on the same rendering-vs-
   orchestration seam as svg.js/axis-handles.js (Task 11). Pure renderers only:
   data in, DOM out, no network, no state. Uses el/fmt (util.js) and svgEl/
   svgRoot (svg.js). Every dollar, bps, rate and book figure comes straight from
   a server response -- nothing here computes a financial number. */

const COST_LINES = new Set(["cost_of_funds", "expected_loss", "operating_cost", "tax"]);
const RULE_BEFORE = new Set(["pre_tax_profit", "net_income"]);
const LABELS = {interest_income: "Interest income", cost_of_funds: "Cost of funds",
  expected_loss: "Expected loss", operating_cost: "Operating cost",
  pre_tax_profit: "Pre-tax profit", tax: "Tax", net_income: "Net income",
  allocated_equity: "Allocated equity"};

// One row per line, dollars and bps both from the response. A cost line stores a
// positive amount that is SUBTRACTED in the waterfall, so its display sign is the
// negation of the stored value (usually "-", but tax flips to a plain positive
// when pre_tax_profit itself is negative -- a rebate, not a further cost). An
// income/subtotal line displays its stored value as-is. Either way the sign
// choice and Math.abs() below are display polarity on a server-given number, the
// same pattern divergingBars (svg.js) already uses for its bar direction -- not
// a new financial figure. A rule marks the two subtotals.
//
// Task 15: the line-increase tab's incremental waterfall shares this exact shape
// (same eight `line` keys, both come from pricing.src.engine.profit_waterfall)
// but its rows carry `dollars` only -- no `bps`. `hasBps` detects that up front so
// the bps column (and `-w.bps`, which would render "NaN bps") is skipped
// entirely rather than defended row by row. `caption` defaults to this tab's own
// text so the pricing call site (tab-pricing.js, no caption arg) is unchanged.
function waterfallTable(lines, ead, caption = "Profit waterfall") {
  // Checks lines[0] only -- assumes a homogeneous set (every line carries `bps`
  // or none do), true of both callers today (profit_waterfall's eight lines,
  // always uniform).
  const hasBps = lines.length > 0 && lines[0].bps !== undefined;
  const body = el("tbody");
  for (const w of lines) {
    const cost = COST_LINES.has(w.line);
    const dEffect = cost ? -w.dollars : w.dollars;
    const sign = dEffect < 0 ? "− " : "";
    const cells = [el("td", {}, LABELS[w.line] || w.line),
                   el("td", {}, sign + fmt.money(Math.abs(dEffect)))];
    if (hasBps) {
      const bEffect = cost ? -w.bps : w.bps;
      cells.push(el("td", {}, sign + fmt.bps(Math.abs(bEffect))));
    }
    body.append(el("tr", {class: RULE_BEFORE.has(w.line) ? "wf-rule" : ""}, ...cells));
  }
  const head = [el("th", {}, "line"), el("th", {}, "dollars")];
  if (hasBps) head.push(el("th", {}, "bps on EAD"));
  const t = el("table", {class: "waterfall"});
  t.append(el("caption", {}, `${caption} — EAD ${fmt.money(ead)}`),
    el("thead", {}, el("tr", {}, ...head)), body);
  return t;
}

// A static axis (no dragging -- this reports) with break-even/hurdle-clearing/
// recommended as plain ticks and the quoted rate as a pin coloured by
// verdict.clears_hurdle. A glyph rides with the colour for greyscale/screen readers.
function rateLadder(rates, verdict) {
  const width = 640, height = 78, pad = {l: 24, r: 24, t: 34};
  const vals = [rates.break_even, rates.hurdle_clearing, rates.recommended, rates.quoted];
  const lo = Math.min(...vals), hi = Math.max(...vals), span = (hi - lo) || 0.01;
  const min = lo - span * 0.15, max = hi + span * 0.15;
  const toX = v => pad.l + (v - min) / (max - min) * (width - pad.l - pad.r);
  const s = svgRoot(width, height);
  const tick = (x, half, w, color) => s.append(svgEl("line",
    {x1: x, x2: x, y1: pad.t - half, y2: pad.t + half, stroke: color, "stroke-width": w}));
  s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: pad.t, y2: pad.t,
    stroke: "var(--ink)", "stroke-width": 2}));
  for (const [key, label] of [["break_even", "break-even"],
      ["hurdle_clearing", "hurdle-clearing"], ["recommended", "recommended"]]) {
    const x = toX(rates[key]);
    tick(x, 8, 2, "var(--muted)");
    const lab = svgEl("text", {x, y: pad.t + 24, "font-size": 11, "text-anchor": "middle"});
    lab.textContent = `${label} ${fmt.pct(rates[key], 2)}`;
    s.append(lab);
  }
  const qx = toX(rates.quoted), color = verdict.clears_hurdle ? "var(--ok)" : "var(--bad)";
  const glyph = verdict.clears_hurdle ? "✓" : "✗";
  tick(qx, 16, 3, color);
  const pin = svgEl("text", {x: qx, y: pad.t - 20, "font-size": 12, "text-anchor": "middle",
    "font-weight": "700", fill: color});
  pin.textContent = `${glyph} quoted ${fmt.pct(rates.quoted, 2)}`;
  s.append(pin);
  const wrap = el("div", {class: "pr-ladder"});
  wrap.append(s, el("p", {class: "shortfall"},
    `${glyph} ${verdict.clears_hurdle ? "clears the hurdle" : "short of the hurdle"} ` +
    `by ${fmt.bps(verdict.rate_shortfall_bps)}`));
  return wrap;
}

function verdictTiles(v) {
  const mk = (label, node) => {
    const d = el("div", {class: "tile"});
    d.append(el("div", {class: "n"}, node), el("div", {class: "k"}, label));
    return d;
  };
  const clears = el("span", {class: "chip " + (v.clears_hurdle ? "Approve" : "Decline")},
    v.clears_hurdle ? "✓ clears" : "✗ short");
  const wrap = el("div", {class: "pr-tiles"});
  wrap.append(mk("ROE at quoted", fmt.pct(v.roe, 2)), mk("ROE hurdle", fmt.pct(v.roe_hurdle, 2)),
    mk("Clears hurdle", clears), mk("Shortfall", fmt.bps(v.rate_shortfall_bps)));
  return wrap;
}

// share_clears and mispriced_ead, sized to watch while a market slider drags --
// this is the session's set-piece (lgd 0.45 -> 0.90 visibly fails the book).
function bookStrip(book) {
  const big = el("div");
  big.append(el("div", {class: "book-share"}, fmt.pct(book.share_clears, 2)),
    el("div", {class: "book-sub"}, `of ${book.n.toLocaleString()} booked loans ` +
      `clear the hurdle (${book.n_clears.toLocaleString()})`));
  const mis = el("div", {class: "book-mispriced"}, el("span", {class: "k"}, "Mispriced EAD"),
    el("span", {class: "n"}, fmt.money(book.mispriced_ead)));
  const wrap = el("div", {class: "pr-book"});
  wrap.append(big, mis);
  return wrap;
}
