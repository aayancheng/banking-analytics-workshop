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
  const values = Object.fromEntries(handles.map(h => [h.key, h.value]));
  let fmtFn = format;

  /* Final review I2: a band edge is a handle KEY (it moves with that handle) or a
     fixed number. The bands used to be drawn once, so dragging t_low to 0.20 left
     the green band at the committed cutoff and the pin sat in amber beside a chip
     that said Approve. Every handle move now re-lays every band. */
  const edge = e => typeof e === "string" ? values[e] : e;
  const bandRects = bands.map(b => {
    const r = svgEl("rect", {y: pad.t - 10, height: 20, fill: b.fill, opacity: 0.25});
    s.append(r);
    return {b, r};
  });
  const layBands = () => {
    for (const {b, r} of bandRects) {
      const x0 = toX(edge(b.from)), x1 = toX(edge(b.to));
      r.setAttribute("x", Math.min(x0, x1));
      r.setAttribute("width", Math.max(0, x1 - x0));
    }
  };
  layBands();
  s.append(svgEl("line", {x1: pad.l, x2: width - pad.r, y1: pad.t,
                          y2: pad.t, stroke: "var(--ink)", "stroke-width": 2}));

  const pt = svgEl("text", {x: 0, y: pad.t - 18, "font-size": 12,
                            "text-anchor": "middle", "font-weight": "600"});
  if (pin !== null) {
    s.append(svgEl("line", {x1: toX(pin), x2: toX(pin), y1: pad.t - 14,
                            y2: pad.t + 14, stroke: "var(--ink)", "stroke-width": 3}));
    pt.setAttribute("x", toX(pin));
    s.append(pt);
  }
  const relabel = [];
  const labelPin = () => { if (pin !== null) pt.textContent = `${pinLabel} ${fmtFn(pin)}`; };
  labelPin();

  for (const h of handles) {
    const g = svgEl("g", {style: "cursor:ew-resize"});
    const tri = svgEl("polygon", {fill: "var(--accent)"});
    const txt = svgEl("text", {"font-size": 12, "text-anchor": "middle",
                               fill: "var(--accent)", y: pad.t + 34});
    const place = v => {
      const x = toX(v);
      tri.setAttribute("points", `${x},${pad.t + 2} ${x - 7},${pad.t + 18} ${x + 7},${pad.t + 18}`);
      txt.setAttribute("x", x);
      txt.textContent = `${h.label} ${fmtFn(v)}`;
    };
    place(h.value);
    relabel.push(() => place(values[h.key]));
    g.append(tri, txt);

    let dragging = false;
    const move = ev => {
      if (!dragging) return;
      const p = s.createSVGPoint();
      p.x = ev.clientX;
      p.y = ev.clientY;
      const v = toV(p.matrixTransform(s.getScreenCTM().inverse()).x);
      values[h.key] = v;
      place(v);
      layBands();
      onChange({...values});
    };
    g.addEventListener("pointerdown", ev => {
      dragging = true;
      // Guarded like releasePointerCapture below: capture can throw (NotFoundError
      // when no active pointer matches the id), and an uncaught throw here would
      // surface as a console error during an otherwise working drag. dragging is set
      // first so the drag still works without capture.
      try { g.setPointerCapture(ev.pointerId); } catch (e) { /* capture is optional */ }
      ev.preventDefault();
    });
    g.addEventListener("pointermove", move);
    g.addEventListener("pointerup", ev => {
      dragging = false;
      try { g.releasePointerCapture(ev.pointerId); } catch (e) { /* already gone */ }
    });
    s.append(g);
  }
  /* The server re-chooses the display precision for the cutoffs just dragged
     (pd_zones.dp / prob_dp); the caller hands the new format here so the pin and
     both handle labels keep printing distinct numbers. Formatting only. */
  s.setFormat = fn => { fmtFn = fn; labelPin(); for (const f of relabel) f(); };
  return s;
}
