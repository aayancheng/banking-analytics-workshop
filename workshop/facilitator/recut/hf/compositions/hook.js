// Shared choreography for the chapter hooks: title in, closer in, everything out.
// hookDuration(default): the hook's length. The root and its clip carry NO static
// data-duration on purpose -- the compiler reads that attribute before any script runs, so
// a variable could never change it. With it absent the render probes the timeline's length
// instead, and the timeline ends at hookOut(tl, DUR, ...). The promo renders each hook at a
// whole number of bars of its music bed (--variables '{"dur":7.245}'); the extra time is
// the closer's hold. The default is the chapter-video length.
function hookDuration(dflt) {
  const v = (window.__hyperframes && window.__hyperframes.getVariables) ? (window.__hyperframes.getVariables() || {}) : {};
  return Number.isFinite(+v.dur) && +v.dur > 0 ? +v.dur : dflt;
}
// One paused timeline per composition; the hook's own scene tweens are added by
// the caller between `hookIn` and `hookOut`.
function hookIn(tl) {
  // the stage as a whole fades in with the title, so static furniture (axes, labels, the
  // carousel's back card) never pops on the first frame -- it matters at the promo's seams
  tl.fromTo("#root .stage", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.45, ease: "power2.out" }, 0.2);
  tl.fromTo("#root .eyebrow", { y: 18, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.5, ease: "power3.out" }, 0.05);
  tl.fromTo("#root h1.title", { y: 26, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.6, ease: "power3.out" }, 0.15);
  tl.fromTo("#root .foot", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.6 }, 0.4);
}
function hookOut(tl, dur, closerAt) {
  tl.fromTo("#root .closer", { y: 22, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.55, ease: "power3.out" }, closerAt);
  tl.to("#root .scene", { autoAlpha: 0, duration: 0.4, ease: "power2.in" }, dur - 0.4);
}
