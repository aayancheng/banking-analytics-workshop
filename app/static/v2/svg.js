"use strict";
/* Inline-SVG primitives for the workbench: static drawing only. No library, no CDN
   -- the page must work offline in a devcontainer. These draw; they never decide
   anything. Every value passed in came from a server response. The one pointer-
   driven primitive, axisWithHandles, lives in axis-handles.js -- it is stateful
   and has real interaction math to get right, which is a different kind of file
   from these. */

const NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}

function svgRoot(width, height) {
  const s = svgEl("svg", {viewBox: `0 0 ${width} ${height}`, width: "100%",
                          height: height, role: "img"});
  return s;
}

/* A 24-point series. y is scaled to the series' own min/max, so a flat series does
   not become noise. `threshold` draws a dashed rule in the series' own units.
   `marker` {value, span, label} draws a server-given quantity as a solid bar over
   the last `span` points -- the number a trigger actually tests, when that is not
   the last point (HIGH_UTILIZATION tests the 3-month mean) -- and the right-hand
   label then names it instead of the last month. Drawn, never computed. */
function sparkline(values, {width = 620, height = 68, threshold = null, marker = null,
                            label = "", format = v => v.toFixed(2)} = {}) {
  const pad = {l: 8, r: 150, t: 10, b: 10};
  const s = svgRoot(width, height);
  const extra = [threshold, marker && marker.value].filter(v => v !== null && v !== undefined);
  const lo = Math.min(...values, ...extra);
  const hi = Math.max(...values, ...extra);
  const span = (hi - lo) || 1;
  const x = i => pad.l + i * (width - pad.l - pad.r) / (values.length - 1);
  const y = v => pad.t + (hi - v) * (height - pad.t - pad.b) / span;

  if (threshold !== null) {
    s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: y(threshold),
                            y2: y(threshold), stroke: "var(--bad)",
                            "stroke-dasharray": "4 3", "stroke-width": 1}));
  }
  s.append(svgEl("polyline", {
    points: values.map((v, i) => `${x(i)},${y(v)}`).join(" "),
    fill: "none", stroke: "var(--accent)", "stroke-width": 2,
    "stroke-linejoin": "round"}));
  s.append(svgEl("circle", {cx: x(values.length - 1), cy: y(values[values.length - 1]),
                            r: 3.5, fill: "var(--accent)"}));
  if (marker) {
    s.append(svgEl("line", {x1: x(values.length - marker.span), x2: x(values.length - 1),
                            y1: y(marker.value), y2: y(marker.value),
                            stroke: "var(--ink)", "stroke-width": 4}));
  }
  const t = svgEl("text", {x: width - pad.r + 8, y: height / 2 + 4,
                           "font-size": 13, fill: "var(--ink)"});
  t.textContent = marker ? `${label} ${marker.label}`
                         : `${label} ${format(values[values.length - 1])}`;
  s.append(t);
  return s;
}

/* Signed contributions around a zero line. Right = pushes PD up. */
function divergingBars(rows, {width = 620, rowHeight = 20,
                              labelWidth = 190, format = v => v.toFixed(3)} = {}) {
  const height = rows.length * rowHeight + 12;
  const s = svgRoot(width, height);
  const mid = labelWidth + (width - labelWidth - 90) / 2;
  const max = Math.max(...rows.map(r => Math.abs(r.contribution))) || 1;
  const scale = (width - labelWidth - 90) / 2 / max;

  s.append(svgEl("line", {x1: mid, x2: mid, y1: 4, y2: height - 4,
                          stroke: "var(--line)"}));
  rows.forEach((r, i) => {
    const yTop = 6 + i * rowHeight;
    const w = Math.abs(r.contribution) * scale;
    const up = r.contribution > 0;
    s.append(svgEl("rect", {x: up ? mid : mid - w, y: yTop, width: w,
                            height: rowHeight - 6, rx: 2,
                            fill: up ? "var(--bad)" : "var(--ok)"}));
    const lab = svgEl("text", {x: 0, y: yTop + rowHeight - 10, "font-size": 12,
                               fill: "var(--ink)"});
    lab.textContent = `${r.feature}  ${fmt.feature(r.value)}`;
    s.append(lab);
    const val = svgEl("text", {x: width - 84, y: yTop + rowHeight - 10,
                               "font-size": 12, fill: "var(--muted)"});
    val.textContent = format(r.contribution);
    s.append(val);
  });
  return s;
}

/* Horizontal bars for the three line-increase caps; the binding one is filled.
   Every bar prints its own amount. A cap at or below zero has no bar to draw, so
   it SAYS "no headroom" with its amount instead of a zero-width bar labelled
   "(binds)" (final review I4: 7,069 of 8,336 binding caps are negative). */
function hbars(rows, {width = 640, rowHeight = 26, labelWidth = 200} = {}) {
  const height = rows.length * rowHeight + 10;
  const s = svgRoot(width, height);
  const barW = width - labelWidth - 190;
  const max = Math.max(...rows.map(r => Math.max(0, r.amount))) || 1;
  rows.forEach((r, i) => {
    const y = 6 + i * rowHeight;
    const w = Math.max(0, r.amount) / max * barW;
    s.append(svgEl("rect", {
      x: labelWidth, y, width: w, height: rowHeight - 10, rx: 2,
      fill: r.binding ? "var(--accent)" : "none",
      stroke: "var(--accent)", "stroke-width": 1}));
    const lab = svgEl("text", {x: 0, y: y + rowHeight - 14, "font-size": 12});
    const open = r.amount > 0;
    lab.textContent = r.name.replace(/_/g, " ") +
      (r.binding ? (open ? "  (binds)" : "  (binds: no headroom)") : "");
    s.append(lab);
    const amt = svgEl("text", {x: labelWidth + w + 6, y: y + rowHeight - 14,
                               "font-size": 12, fill: "var(--ink)"});
    amt.textContent = open ? fmt.money(r.amount)
      : (r.binding ? `cap ${fmt.money(r.amount)}` : `no headroom (cap ${fmt.money(r.amount)})`);
    s.append(amt);
  });
  return s;
}
