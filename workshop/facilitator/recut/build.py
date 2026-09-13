#!/usr/bin/env python3
"""Recut a session recording: cut list -> segments with overlays -> one MP4.

    python build.py S1.cuts.json graphics   # render the HyperFrames pieces (once)
    python build.py S1.cuts.json draft      # 960-px quick build for checking the cut
    python build.py S1.cuts.json final      # full quality
    python build.py S1.cuts.json all        # graphics + final
    python build.py S1.cuts.json final --only K5 --keep-segments   # rebuild one piece

Division of labour, on purpose:
  * HyperFrames renders the GRAPHICS -- intro/outro cards (MP4), chapter
    lower-thirds and callouts (ProRes 4444 MOV with alpha), the watermark (PNG).
    Seconds of footage each; headless Chrome is the right tool for that.
  * ffmpeg does the CUT and the COMPOSITING. Each kept range is extracted once
    with the watermark and its timed overlays baked in, in parallel, to an MPEG-TS
    intermediate; the pieces are then concatenated with stream copy, so the
    lecture footage is encoded exactly once.

Stdlib + ffmpeg + `npx hyperframes`. Inputs and outputs live in a gitignored
folder (see README.md); only this tooling is tracked.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # repo root
HF = HERE / "hf"                # HyperFrames project
HF_CLI = ["npx", "--yes", "hyperframes@0.8.36"]

VIDEO_FINAL = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high"]
VIDEO_DRAFT = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p"]
AUDIO = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def run(cmd, log: Path | None = None, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if log:
        log.write_text(" ".join(map(str, cmd)) + "\n\n" + p.stdout + p.stderr)
    if p.returncode != 0:
        tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    return p


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


# --------------------------------------------------------------------------- graphics
def graphics(doc, out: Path, force: bool):
    g = out / "graphics"
    g.mkdir(parents=True, exist_ok=True)
    comps = HF / "compositions"
    shared = [comps / "shared.css", comps / "shared.js"]

    def stale(target: Path, *sources: Path) -> bool:
        if force or not target.exists():
            return True
        return target.stat().st_mtime < max(s.stat().st_mtime for s in (*sources, *shared))

    def render(src: Path, target: Path, fmt_: str, extra=()):
        if not stale(target, src):
            print(f"  up to date  {target.name}")
            return
        t0 = time.time()
        tmp = target.with_suffix(".tmp" + target.suffix) if fmt_ != "png-sequence" else target
        cmd = [*HF_CLI, "render", "-c", str(src.relative_to(HF)), "--format", fmt_, "--fps", str(doc["fps"]),
               *extra, "-o", str(tmp)]
        run(cmd, out / "logs" / f"render-{target.stem}.log", cwd=HF)
        if fmt_ != "png-sequence":
            tmp.replace(target)
        print(f"  rendered    {target.name}  ({time.time() - t0:.0f}s)")

    (out / "logs").mkdir(exist_ok=True)
    # watermark -> one PNG
    wm_dir = g / "watermark"
    if stale(g / "watermark.png", comps / "watermark.html"):
        shutil.rmtree(wm_dir, ignore_errors=True)
        render(comps / "watermark.html", wm_dir, "png-sequence")
        shutil.copy(next(wm_dir.glob("*.png")), g / "watermark.png")
        shutil.rmtree(wm_dir)
    else:
        print("  up to date  watermark.png")
    # cards
    for key in ("intro", "outro"):
        render(comps / f"{doc['cards'][key]}.html", g / f"{key}.mp4", "mp4", ["--quality", "high"])
    # chapters: one composition, many renders
    for c in doc["chapters"]:
        vars_ = json.dumps({"num": str(c["num"]), "title": c["title"]}, ensure_ascii=False)
        target = g / f"ch{c['num']}.mov"
        # the variables are part of the "source": remember them beside the render
        stamp = target.with_suffix(".vars")
        if stale(target, comps / "chapter.html") or not stamp.exists() or stamp.read_text() != vars_:
            target.unlink(missing_ok=True)
            render(comps / "chapter.html", target, "mov", ["--variables", vars_])
            stamp.write_text(vars_)
        else:
            print(f"  up to date  {target.name}")
    # callouts
    for c in doc["callouts"]:
        render(comps / "callouts" / f"{c['id']}.html", g / f"{c['id']}.mov", "mov")


# --------------------------------------------------------------------------- segments
def overlays_for(doc, keep):
    """(local_start, dur, file) for every chapter/callout inside this keep."""
    items = []
    for c in doc["chapters"]:
        if keep["in"] <= c["at"] < keep["out"]:
            items.append((c["at"] - keep["in"], c["dur"], f"ch{c['num']}.mov"))
    for c in doc["callouts"]:
        if keep["in"] <= c["at"] < keep["out"]:
            items.append((c["at"] - keep["in"], c["dur"], f"{c['id']}.mov"))
    return sorted(items)


def segment_cmd(doc, keep, src: Path, g: Path, target: Path, draft: bool):
    length = round(keep["out"] - keep["in"], 3)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y",
           "-ss", f"{keep['in']:.3f}", "-t", f"{length:.3f}", "-i", str(src),
           "-i", str(g / "watermark.png")]
    ov = overlays_for(doc, keep)
    for local, dur, name in ov:
        cmd += ["-itsoffset", f"{local:.3f}", "-i", str(g / name)]

    chain = ["[0:v][1:v]overlay=0:0[v0]"]
    last = "v0"
    for i, (local, dur, _) in enumerate(ov):
        nxt = f"v{i + 1}"
        chain.append(f"[{last}][{i + 2}:v]overlay=0:0:eof_action=pass:"
                     f"enable='between(t,{local:.3f},{local + dur:.3f})'[{nxt}]")
        last = nxt
    if draft:
        chain.append(f"[{last}]scale=960:-2[vout]")
        last = "vout"
    a = doc["audio"]
    chain.append(f"[0:a]volume={a['gain_db']}dB,alimiter=limit={a['limit']}:attack=5:release=50,"
                 f"afade=t=in:st=0:d=0.05,afade=t=out:st={max(length - 0.05, 0):.3f}:d=0.05,"
                 f"apad=whole_dur={length:.3f}[aout]")   # audio exactly as long as the video: no gap at the seam
    cmd += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "[aout]",
            *(VIDEO_DRAFT if draft else VIDEO_FINAL), "-r", str(doc["fps"]), *AUDIO,
            "-f", "mpegts", str(target)]
    return cmd


def card_cmd(doc, src: Path, target: Path, draft: bool):
    vf = ["-vf", "scale=960:-2"] if draft else []
    length = duration(src)  # explicit -t: -shortest lets the silent track end a few frames early
    return ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(src),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{length:.3f}",
            *vf, *(VIDEO_DRAFT if draft else VIDEO_FINAL), "-r", str(doc["fps"]), *AUDIO,
            "-f", "mpegts", str(target)]


def build(doc, out: Path, draft: bool, only: str | None, keep_segments: bool, workers: int):
    src = ROOT / doc["source"]
    g = out / "graphics"
    seg = out / ("segments-draft" if draft else "segments")
    seg.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    jobs = []
    for key in ("intro", "outro"):
        t = seg / f"{key}.ts"
        if only and only != key:
            continue
        if keep_segments and t.exists():
            continue
        jobs.append((key, card_cmd(doc, g / f"{key}.mp4", t, draft)))
    for k in doc["keeps"]:
        t = seg / f"{k['id']}.ts"
        if only and only != k["id"]:
            continue
        if keep_segments and t.exists():
            continue
        jobs.append((k["id"], segment_cmd(doc, k, src, g, t, draft)))

    print(f"{len(jobs)} ffmpeg jobs, {workers} at a time ({'draft' if draft else 'final'})")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run, cmd, out / "logs" / f"{name}{'-draft' if draft else ''}.log"): name for name, cmd in jobs}
        for f in as_completed(futs):
            name = futs[f]
            f.result()  # raises with the ffmpeg tail on failure
            print(f"  done {name:<6} {time.time() - t0:5.0f}s")

    # concat, in order: intro, keeps, outro
    order = [seg / "intro.ts", *(seg / f"{k['id']}.ts" for k in doc["keeps"]), seg / "outro.ts"]
    missing = [p.name for p in order if not p.exists()]
    if missing:
        sys.exit(f"cannot concat, missing: {missing}")
    lst = seg / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in order))
    final = out / ("S1-draft.mp4" if draft else "S1-compact.mp4")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart", str(final)],
        out / "logs" / f"concat{'-draft' if draft else ''}.log")

    # report: expected vs actual, and where each graphic lands in OUTPUT time
    expected = sum(duration(p) for p in order)
    actual = duration(final)
    print(f"\n{final.name}: {fmt(actual)}  (pieces sum to {fmt(expected)}, "
          f"{'OK' if abs(actual - expected) < 0.5 else 'MISMATCH'})  {final.stat().st_size / 1e6:.0f} MB")
    print("\noutput-time map (source -> output):")
    offset = duration(seg / "intro.ts")
    rows = []
    for k in doc["keeps"]:
        rows.append((offset, f"{k['id']:<4} {fmt(k['in'])}-{fmt(k['out'])}  {k['note'][:60]}"))
        for c in doc["chapters"]:
            if k["in"] <= c["at"] < k["out"]:
                rows.append((offset + c["at"] - k["in"], f"     chapter {c['num']}: {c['title']}"))
        for c in doc["callouts"]:
            if k["in"] <= c["at"] < k["out"]:
                rows.append((offset + c["at"] - k["in"], f"     callout {c['id']}"))
        offset += duration(seg / f"{k['id']}.ts")
    rows.append((offset, "outro"))
    for t, label in sorted(rows):
        print(f"  {fmt(t)}  {label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("stage", choices=["graphics", "draft", "final", "all"])
    ap.add_argument("--only", help="rebuild a single piece: K5, intro, outro")
    ap.add_argument("--keep-segments", action="store_true", help="reuse existing .ts pieces")
    ap.add_argument("--force", action="store_true", help="re-render graphics even if up to date")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    doc = json.loads(Path(a.cuts).read_text())
    out = ROOT / doc["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    if a.stage in ("graphics", "all"):
        graphics(doc, out, a.force)
    if a.stage == "draft":
        build(doc, out, True, a.only, a.keep_segments, a.workers)
    if a.stage in ("final", "all"):
        build(doc, out, False, a.only, a.keep_segments, a.workers)


if __name__ == "__main__":
    main()
