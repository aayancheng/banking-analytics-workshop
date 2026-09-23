"use strict";
/* Inline-SVG primitives for the workbench. No library, no CDN -- the page must work
   offline in a devcontainer. These draw; they never decide anything. Every value
   passed in came from a server response. */

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
   not become noise. `threshold` draws a dashed rule in the series' own units. */
function sparkline(values, {width = 620, height = 68, threshold = null,
                            label = "", format = v => v.toFixed(2)} = {}) {
  const pad = {l: 8, r: 96, t: 10, b: 10};
  const s = svgRoot(width, height);
  const lo = Math.min(...values, threshold === null ? Infinity : threshold);
  const hi = Math.max(...values, threshold === null ? -Infinity : threshold);
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
  const t = svgEl("text", {x: width - pad.r + 8, y: height / 2 + 4,
                           "font-size": 13, fill: "var(--ink)"});
  t.textContent = `${label} ${format(values[values.length - 1])}`;
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
    lab.textContent = `${r.feature}  ${r.value ?? ""}`;
    s.append(lab);
    const val = svgEl("text", {x: width - 84, y: yTop + rowHeight - 10,
                               "font-size": 12, fill: "var(--muted)"});
    val.textContent = format(r.contribution);
    s.append(val);
  });
  return s;
}

/* Horizontal bars for the three line-increase caps; the binding one is filled. */
function hbars(rows, {width = 560, rowHeight = 26, labelWidth = 200} = {}) {
  const height = rows.length * rowHeight + 10;
  const s = svgRoot(width, height);
  const max = Math.max(...rows.map(r => Math.abs(r.amount))) || 1;
  rows.forEach((r, i) => {
    const y = 6 + i * rowHeight;
    const w = Math.max(0, r.amount) / max * (width - labelWidth - 110);
    s.append(svgEl("rect", {
      x: labelWidth, y, width: w, height: rowHeight - 10, rx: 2,
      fill: r.binding ? "var(--accent)" : "none",
      stroke: "var(--accent)", "stroke-width": 1}));
    const lab = svgEl("text", {x: 0, y: y + rowHeight - 14, "font-size": 12});
    lab.textContent = r.name.replace(/_/g, " ") + (r.binding ? "  (binds)" : "");
    s.append(lab);
  });
  return s;
}

/* An axis carrying draggable threshold handles and one fixed pin.
   `handles` is [{key, value, label}]; onChange({key: value, ...}) fires on drag,
   debounced by the caller. The axis NEVER decides anything -- it reports a number
   and the server recomputes. */
function axisWithHandles(
    {min = 0, max = 1, pin = null, pinLabel = "", handles = [], bands = [],
     width = 640, height = 76, format = v => v.toFixed(4)}, onChange) {
  const pad = {l: 20, r: 20, t: 26, b: 22};
  const s = svgRoot(width, height);
  const innerW = width - pad.l - pad.r;
  const toX = v => pad.l + (v - min) / (max - min) * innerW;
  const toV = x => Math.min(max, Math.max(min,
                     min + (x - pad.l) / innerW * (max - min)));

  for (const b of bands) {
    s.append(svgEl("rect", {x: toX(b.from), y: pad.t - 10,
                            width: Math.max(0, toX(b.to) - toX(b.from)),
                            height: 20, fill: b.fill, opacity: 0.25}));
  }
  s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: pad.t,
                          y2: pad.t, stroke: "var(--ink)", "stroke-width": 2}));

  if (pin !== null) {
    s.append(svgEl("line", {x1: toX(pin), x2: toX(pin), y1: pad.t - 14,
                            y2: pad.t + 14, stroke: "var(--ink)", "stroke-width": 3}));
    const pt = svgEl("text", {x: toX(pin), y: pad.t - 18, "font-size": 12,
                              "text-anchor": "middle", "font-weight": "600"});
    pt.textContent = `${pinLabel} ${format(pin)}`;
    s.append(pt);
  }

  const values = Object.fromEntries(handles.map(h => [h.key, h.value]));
  for (const h of handles) {
    const g = svgEl("g", {style: "cursor:ew-resize"});
    const tri = svgEl("polygon", {fill: "var(--accent)"});
    const txt = svgEl("text", {"font-size": 12, "text-anchor": "middle",
                               fill: "var(--accent)", y: pad.t + 34});
    const place = v => {
      const x = toX(v);
      tri.setAttribute("points", `${x},${pad.t + 2} ${x - 7},${pad.t + 18} ${x + 7},${pad.t + 18}`);
      txt.setAttribute("x", x);
      txt.textContent = `${h.label} ${format(v)}`;
    };
    place(h.value);
    g.append(tri, txt);

    let dragging = false;
    const move = ev => {
      if (!dragging) return;
      const box = s.getBoundingClientRect();
      const x = (ev.clientX - box.left) / box.width * width;
      const v = toV(x);
      values[h.key] = v;
      place(v);
      onChange({...values});
    };
    g.addEventListener("pointerdown", ev => {
      dragging = true; g.setPointerCapture(ev.pointerId); ev.preventDefault();
    });
    g.addEventListener("pointermove", move);
    g.addEventListener("pointerup", ev => {
      dragging = false;
      try { g.releasePointerCapture(ev.pointerId); } catch (e) { /* already gone */ }
    });
    s.append(g);
  }
  return s;
}
