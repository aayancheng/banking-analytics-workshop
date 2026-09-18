#!/usr/bin/env python3
"""Align a Zoom transcript to the recording, then read it in video time.

Zoom's transcript is wall-clock (HH:MM:SS of the meeting); the recording starts whenever
you pressed Record, so `video_t = wall_t - offset`. This finds the offset, writes a copy of
the transcript in video time with attendees anonymised, and prints the pauses + cue text
around any point -- the three things you need to author a cut list.

    python align.py S2.cuts.json offset            # find the offset, store it in the cuts file
    python align.py S2.cuts.json dump              # <transcript>.videotime.txt, attendees -> ATTENDEE-A..
    python align.py S2.cuts.json window 19:10 +20  # pauses (>=0.3 s) and cue text in that window
    python align.py S2.cuts.json window 19:10 +20 --noise -32 --min 0.6

The cuts file needs `source` (the MP4) and `transcript` (the Zoom .txt/.vtt). `offset`
writes `transcript_offset` (seconds) back into it; `dump` and `window` read it.

How `offset` works: cue gaps >= 1.5 s in the transcript should coincide with silences in
the audio. It scans every feasible offset in 0.25 s steps and counts coincidences; the
peak is the offset. Cross-check it once against the macOS menu-bar clock, which is in every
frame of a screen share: `ffmpeg -ss T -i src.mp4 -frames:v 1 -vf crop=520:26:1400:0 clock.png`.
Stdlib + ffmpeg only.
"""
import argparse
import bisect
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CUE = re.compile(r"(\d\d):(\d\d):(\d\d)(?:[.,]\d+)? --> (\d\d):(\d\d):(\d\d)")


def hms(h, m, s):
    return int(h) * 3600 + int(m) * 60 + int(s)


def fmt(t: float) -> str:
    sign = "-" if t < 0 else ""
    t = abs(t)
    return f"{sign}{int(t // 60):02d}:{t % 60:05.2f}"


def parse_transcript(path: Path):
    """[(start_wall, end_wall, speaker, text)] -- Zoom's 'HH:MM:SS --> HH:MM:SS' + 'Name: text'."""
    cues, cur = [], None
    for line in path.read_text(errors="replace").splitlines():
        m = CUE.match(line)
        if m:
            cur = (hms(*m.groups()[:3]), hms(*m.groups()[3:]))
            continue
        if cur and ":" in line:
            spk, txt = line.split(":", 1)
            cues.append((cur[0], cur[1], spk.strip(), txt.strip()))
            cur = None
    if not cues:
        sys.exit(f"no cues parsed from {path}")
    return cues


def pauses(source: Path, noise=-32, min_dur=0.6, start=None, length=None, cache=True):
    """[(start, end)] silences via silencedetect after a 120 Hz high-pass."""
    cache_path = source.with_suffix(f".pauses{noise}_{min_dur}.json")
    if cache and start is None and cache_path.exists():
        return [tuple(p) for p in json.loads(cache_path.read_text())]
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}", "-t", f"{length:.3f}"]
    cmd += ["-i", str(source), "-vn", "-af", f"highpass=f=120,silencedetect=noise={noise}dB:d={min_dur}",
            "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    base = start or 0.0
    st, out = None, []
    for kind, v in re.findall(r"silence_(start|end): ([0-9.]+)", err):
        if kind == "start":
            st = float(v) + base
        else:
            out.append((st, float(v) + base))
    if cache and start is None:
        cache_path.write_text(json.dumps(out))
    return out


def duration(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout)


def find_offset(cues, ps, video_len: float):
    gaps = [((b + c) / 2) for (_, b, _, _), (c, _, _, _) in zip(cues, cues[1:]) if 1.5 <= c - b <= 12]
    if len(gaps) < 8:
        sys.exit(f"only {len(gaps)} usable transcript gaps; cannot align")
    starts = [s for s, _ in ps]
    def hit(v):
        i = bisect.bisect_right(starts, v + 0.3) - 1
        return i >= 0 and ps[i][0] - 0.3 <= v <= ps[i][1] + 0.3
    lo = cues[0][0] - 120                      # recording cannot start much before the first cue
    hi = cues[-1][1] - video_len + 120         # ...or end much after the last one
    best = []
    off = lo
    while off <= hi:
        score = sum(1 for g in gaps if 0 <= g - off <= video_len and hit(g - off))
        best.append((score, off))
        off += 0.25
    best.sort(reverse=True)
    # a plateau of equal scores is normal (cue times are whole seconds): take its middle
    top = [off for sc, off in best if sc == best[0][0]]
    best.insert(0, (best[0][0], sorted(top)[len(top) // 2]))
    return best[:6], len(gaps)


def wall(t: float) -> str:
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("cmd", choices=["offset", "dump", "window"])
    ap.add_argument("at", nargs="?", help="window: MM:SS (video time)")
    ap.add_argument("length", nargs="?", help="window: +seconds (default +20)")
    ap.add_argument("--noise", type=float, default=-30, help="window: silencedetect dB (default -30)")
    ap.add_argument("--min", type=float, default=0.3, help="window: min pause s (default 0.3)")
    a = ap.parse_args()

    path = Path(a.cuts)
    doc = json.loads(path.read_text())
    source = ROOT / doc["source"]
    transcript = ROOT / doc["transcript"]
    cues = parse_transcript(transcript)
    names = sorted({s for _, _, s, _ in cues if not s.lower().startswith("yan")})
    alias = {n: f"ATTENDEE-{chr(65 + i)}" for i, n in enumerate(names)}
    who = lambda s: "YAN" if s.lower().startswith("yan") else alias[s]

    if a.cmd == "offset":
        vlen = duration(source)
        ps = pauses(source)
        top, n = find_offset(cues, ps, vlen)
        print(f"{len(cues)} cues, {n} usable gaps, {len(ps)} pauses, video {fmt(vlen)}")
        for score, off in top:
            print(f"  offset {wall(off)}  hits {score}/{n}")
        score, off = top[0]
        runner = top[1][0] if len(top) > 1 else 0
        doc["transcript_offset"] = round(off, 2)
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote transcript_offset = {off:.2f} s ({wall(off)}) to {path.name}")
        if score - runner <= 1 and abs(top[1][1] - off) > 1.0:
            print("  ⚠️ peak is not clear-cut -- cross-check with the menu-bar clock before trusting it")
        return

    off = doc.get("transcript_offset")
    if off is None:
        sys.exit("no transcript_offset in the cuts file -- run `offset` first")

    if a.cmd == "dump":
        out = transcript.with_suffix(".videotime.txt")
        para = []
        for s, e, spk, txt in cues:
            w = who(spk)
            if para and para[-1][2] == w and s - para[-1][1] < 8 and len(para[-1][3]) < 420:
                para[-1] = (para[-1][0], e, w, para[-1][3] + " " + txt)
            else:
                para.append((s, e, w, txt))
        out.write_text("".join(f"[{fmt(s - off)}–{fmt(e - off)}] {w}: {t}\n" for s, e, w, t in para))
        print(f"wrote {out}  ({len(para)} paragraphs; {len(names)} attendee(s) anonymised; "
              f"negative times are before the recording started)")
        return

    if a.cmd == "window":
        if not a.at:
            sys.exit("window needs a video time, e.g. 19:10 +20")
        m, s = a.at.split(":")
        t0 = int(m) * 60 + float(s)
        length = float((a.length or "+20").lstrip("+"))
        print(f"### video {fmt(t0)} +{length:.0f}s   (wall {wall(t0 + off)})")
        for s_, e_ in pauses(source, a.noise, a.min, start=t0, length=length, cache=False):
            print(f"   pause {fmt(s_)} - {fmt(e_)}  ({e_ - s_:.2f}s)")
        for s_, e_, spk, txt in cues:
            vs, ve = s_ - off, e_ - off
            if ve >= t0 and vs <= t0 + length:
                print(f"   [{fmt(vs)}-{fmt(ve)}] {who(spk)}: {txt[:160]}")


if __name__ == "__main__":
    main()
