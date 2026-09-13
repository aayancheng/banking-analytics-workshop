// One paused GSAP timeline per composition, registered under its composition id.
// The timed element is the full-frame `.clip` wrapper; we animate the inner panel,
// never the clip itself (the framework owns clip visibility).
function lowerThirdTimeline(compId, panel, dur) {
  const tl = gsap.timeline({ paused: true });
  tl.fromTo(panel, { x: -60, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.55, ease: "power3.out" }, 0);
  tl.fromTo(panel + " .kicker", { y: 10, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.4, ease: "power2.out" }, 0.25);
  tl.fromTo(panel + " .main", { y: 14, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.45, ease: "power2.out" }, 0.35);
  tl.to(panel, { x: -40, autoAlpha: 0, duration: 0.45, ease: "power2.in" }, dur - 0.6);
  window.__timelines[compId] = tl;
  return tl;
}
