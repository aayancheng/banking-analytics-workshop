#!/usr/bin/env python3
"""Burned-in captions for a recut: cleaned cue text -> timed two-line captions -> one
HyperFrames render of every caption as a transparent PNG -> what build.py overlays.

    python captions.py S4.cuts.json             # segments + caption PNGs (one render)
    python captions.py S4-ch3.cuts.json --srt   # after build.py final: out/<stem>.srt

The cuts file names the caption sources in `"captions"`:
    {"clean": "<path>.json", "vtt": "<path>.vtt"}                      # the lecture
    {"extra": [{"source": "<pickup.mp4>", "segments": [[start, end, text], ...]}]}

`clean` holds `{"cues": {"<vtt cue number>": "cleaned text", ...}, "notes": [{at, dur, text}]}`:
the cue's TIMES come from the VTT, its TEXT from `clean` (cues missing from `clean` are
dropped). Each cue is split at sentence/clause breaks into captions of at most two lines,
timed in proportion to their length. Notes are bracketed captions for silent stretches.

This ffmpeg has no libass, so captions are images: one composition (`<stem>-captions.html`,
local only) shows caption i during second i; rendering it as a 1 fps png-sequence yields
caption_000i.png. build.py overlays them with a concat list per piece, so the footage is
still encoded exactly once. They sit at the TOP of the frame, over the Mac menu bar and
browser tabs: the bottom belongs to the callouts and the watermark.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HF = HERE / "hf"
MAX_LINE = 46          # characters per line; two lines per caption
MIN_DUR = 1.2


def vtt_cues(path: Path):
    txt = path.read_text(errors="replace")
    out = {}
    for m in re.finditer(r"(\d+)\n(\d\d):(\d\d):(\d\d)\.(\d+) --> (\d\d):(\d\d):(\d\d)\.(\d+)", txt):
        a = int(m[2]) * 3600 + int(m[3]) * 60 + int(m[4]) + int(m[5]) / 1000
        b = int(m[6]) * 3600 + int(m[7]) * 60 + int(m[8]) + int(m[9]) / 1000
        out[m[1]] = (a, b)
    return out


def wrap(text: str):
    """One line if it fits; otherwise two lines split at the space nearest the middle
    (balanced, so a caption never ends on a one-word orphan). Returns [] for 3+ lines."""
    if len(text) <= MAX_LINE:
        return [text]
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    best = min(spaces, key=lambda i: abs(i - len(text) / 2), default=None)
    if best is None:
        return [text]
    a, b = text[:best], text[best + 1:]
    if len(a) > MAX_LINE or len(b) > MAX_LINE:
        # unbalanced text: greedy fill, may produce 3+ lines
        lines, cur = [], ""
        for w in text.split():
            if cur and len(cur) + 1 + len(w) > MAX_LINE:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        return lines + ([cur] if cur else [])
    return [a, b]


def chunks(text: str):
    """Split a cue into captions of <= 2 lines: sentences first, then clauses at commas or
    dashes, then words -- whichever keeps each caption a readable unit."""
    def fits(t): return len(wrap(t)) <= 2
    def split_units(t, pattern):
        return [u for u in re.split(pattern, t) if u]
    out = []
    def place(units, deeper):
        cur = ""
        for u in units:
            cand = (cur + " " + u).strip()
            if fits(cand):
                cur = cand; continue
            if cur: out.append(cur)
            if fits(u): cur = u
            else: deeper(u); cur = ""
        if cur: out.append(cur)
    def by_words(t):
        words, take = t.split(), []
        while words:
            if take and not fits(" ".join(take + [words[0]])):
                out.append(" ".join(take)); take = []
            take.append(words.pop(0))
        if take: out.append(" ".join(take))
    def by_clause(t): place(split_units(t, r"(?<=[,;—])\s+"), by_words)
    place(split_units(text, r"(?<=[.?!:])\s+"), by_clause)
    # a fragment ("You can say:", a lone dash) reads as a flash: fold it into a neighbour
    i = 0
    while i < len(out):
        if len(out[i].strip(" —-")) < 20 and len(out) > 1:
            if i + 1 < len(out) and fits(out[i] + " " + out[i + 1]):
                out[i:i + 2] = [out[i] + " " + out[i + 1]]; continue
            if i > 0 and fits(out[i - 1] + " " + out[i]):
                out[i - 1:i + 1] = [out[i - 1] + " " + out[i]]; i -= 1; continue
            if not out[i].strip(" —-"):
                del out[i]; continue
        i += 1
    return out


def segments(doc):
    cap = doc["captions"]
    segs = []
    if cap.get("clean"):
        clean = json.loads((ROOT / cap["clean"]).read_text())
        times = vtt_cues(ROOT / cap["vtt"])
        for num, text in clean["cues"].items():
            if num not in times:
                sys.exit(f"cue {num} is not in the VTT")
            a, b = times[num]
            cs = chunks(text)
            total = sum(len(c) for c in cs)
            t = a
            for c in cs:
                d = (b - a) * len(c) / total
                segs.append({"source": None, "start": round(t, 3), "end": round(t + d, 3), "text": c})
                t += d
        for n in clean.get("notes", []):
            segs.append({"source": None, "start": n["at"], "end": n["at"] + n["dur"], "text": n["text"], "note": True})
    for x in cap.get("extra", []):
        for a, b, text in x["segments"]:
            for c in [text] if len(wrap(text)) <= 2 else chunks(text):
                segs.append({"source": x["source"], "start": a, "end": b, "text": c})
    segs.sort(key=lambda s: (s["source"] or "", s["start"]))
    # no overlaps within a source; stretch very short captions where there is room
    for i, s in enumerate(segs):
        nxt = segs[i + 1] if i + 1 < len(segs) and segs[i + 1]["source"] == s["source"] else None
        if nxt and s["end"] > nxt["start"]:
            s["end"] = nxt["start"]
        if s["end"] - s["start"] < MIN_DUR:
            limit = nxt["start"] if nxt else s["start"] + MIN_DUR
            s["end"] = min(s["start"] + MIN_DUR, limit)
    for i, s in enumerate(segs):
        s["png"] = f"caption_{i + 1:04d}.png"
    return segs


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1920, height=1080" />
<title>{stem} captions</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<link rel="stylesheet" href="shared.css" />
<style>
  html, body {{ background: transparent; }}
  .clip {{ position: absolute; inset: 0; }}
  .cap {{ position: absolute; left: 50%; top: 18px; transform: translateX(-50%); max-width: 1560px;
         padding: 12px 30px 14px; border-radius: 12px; background: rgba(15, 22, 32, 0.86);
         color: #fff; font-size: 40px; font-weight: 600; line-height: 1.28; text-align: center;
         box-shadow: 0 8px 26px rgba(0, 0, 0, 0.35); white-space: pre-line; }}
  .cap.note {{ color: #ffd7a8; font-style: italic; font-weight: 500; }}
</style></head><body>
<div id="root" data-composition-id="{stem}-captions" data-start="0" data-duration="{n}" data-width="1920" data-height="1080">
{clips}
</div>
<script>window.__timelines["{stem}-captions"] = gsap.timeline({{ paused: true }});</script>
</body></html>
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(doc, segs, out: Path, force: bool):
    stem = doc["stem"].split("-ch")[0]
    cdir = out / "graphics" / f"{stem}-captions"
    stamp = cdir / "segments.json"
    if not force and stamp.exists() and json.loads(stamp.read_text()) == segs:
        print(f"  up to date  {len(segs)} captions in {cdir.name}/")
        return cdir
    clips = "\n".join(
        f'  <div class="clip" data-start="{i}" data-duration="1" data-track-index="1">'
        f'<div class="cap{" note" if s.get("note") else ""}">{esc(chr(10).join(wrap(s["text"])))}</div></div>'
        for i, s in enumerate(segs))
    comp = HF / "compositions" / f"{stem}-captions.html"
    comp.write_text(PAGE.format(stem=stem, n=len(segs), clips=clips))
    shutil.rmtree(cdir, ignore_errors=True)
    tmp = out / "graphics" / f"{stem}-captions-render"
    shutil.rmtree(tmp, ignore_errors=True)
    pin = re.search(r"hyperframes@(\d+\.\d+\.\d+)", (HF / "package.json").read_text()).group(1)
    cmd = ["npx", "--yes", f"hyperframes@{pin}", "render", "-c", str(comp.relative_to(HF)),
           "--format", "png-sequence", "--fps", "1", "--low-memory-mode", "-o", str(tmp)]
    print(f"  rendering {len(segs)} captions …")
    r = subprocess.run(cmd, cwd=HF, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-2000:] + r.stderr[-2000:])
    frames = sorted(tmp.rglob("*.png"))
    if len(frames) < len(segs):
        sys.exit(f"expected {len(segs)} frames, got {len(frames)}")
    cdir.mkdir(parents=True)
    for s, f in zip(segs, frames):
        f.replace(cdir / s["png"])
    # a fully transparent frame for the gaps between captions
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black@0.0:s=1920x1080,format=rgba",
                    "-frames:v", "1", str(cdir / "blank.png")], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    stamp.write_text(json.dumps(segs))
    print(f"  rendered    {len(segs)} captions → {cdir}")
    return cdir


def fmt_srt(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(doc, segs, out: Path):
    """Map captions through the built video's output-time map (piece order, video-stream lengths)."""
    sys.path.insert(0, str(HERE))
    import build
    stem = doc["stem"]
    seg_dir = out / f"segments-{stem}"
    offset, lines, n = 0.0, [], 0
    for pc in build.pieces(doc):
        ts = seg_dir / f"{pc['name']}.ts"
        length = build.vduration(ts) if ts.exists() else (pc["out"] - pc["in"] if pc["kind"] == "keep" else None)
        if length is None:
            sys.exit(f"need {ts} (build with --keep-segments, or keep the segments) to time the SRT")
        if pc["kind"] == "keep":
            src = pc.get("source")
            for s in segs:
                if s["source"] == src and s["end"] > pc["in"] and s["start"] < pc["out"]:
                    a = offset + max(s["start"], pc["in"]) - pc["in"]; b = offset + min(s["end"], pc["out"]) - pc["in"]
                    n += 1
                    lines += [str(n), f"{fmt_srt(a)} --> {fmt_srt(b)}", "\n".join(wrap(s["text"])), ""]
        offset += length
    path = out / f"{stem}.srt"
    path.write_text("\n".join(lines))
    print(f"wrote {path.name}: {n} captions")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("--srt", action="store_true", help="write out/<stem>.srt from a built video's segments")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    doc = json.loads(Path(a.cuts).read_text())
    out = ROOT / doc.get("out_dir", "workshop/LectureSummaryandRecordings/out")
    segs = segments(doc)
    if a.srt:
        write_srt(doc, segs, out)
    else:
        render(doc, segs, out, a.force)


if __name__ == "__main__":
    main()
