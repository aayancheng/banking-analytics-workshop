"use strict";
/* The one pointer-driven SVG primitive, split out from svg.js on purpose: it is
   stateful and has real interaction math to get wrong, which svgEl/sparkline/
   divergingBars/hbars do not. Depends on svgEl/svgRoot from svg.js (script order
   in index.html loads svg.js first). */

/* An axis carrying draggable threshold handles and one fixed pin.
   `handles` is [{key, value, label}]; onChange({key: value, ...}) fires on drag,
   debounced by the caller. The axis NEVER decides anything -- it reports a number
   and the server recomputes.

   Pointer mapping: svgRoot sets width:"100%" with a fixed pixel height, so
   preserveAspectRatio's default (xMidYMid meet) letterboxes the drawing whenever
   the rendered box's aspect ratio doesn't match the viewBox's -- which it usually
   won't, since the box just fills whatever column it sits in. A naive
   (clientX - box.left) / box.width * width assumes no letterboxing and is wrong
   by exactly the letterbox margin: measured live at a 784px-wide container against
   a 640-wide viewBox, that is up to 55px of error (8.6% of the axis) at the ends,
   zero at the centre -- and it vanishes entirely at some other width by
   coincidence, not because it's correct. Mapping through the SVG's own screen CTM
   (current transformation matrix) accounts for the actual letterboxed scale and
   offset at any container size, so it is exact everywhere. */
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
      const pt = s.createSVGPoint();
      pt.x = ev.clientX;
      pt.y = ev.clientY;
      const v = toV(pt.matrixTransform(s.getScreenCTM().inverse()).x);
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
