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
  * A chapter is a FREEZE: the chapter's first frame held (silent) while the
    banner rises to mid-left and holds; the footage resumes as it drops out.
    Chapter marks are embedded in the MP4 and written out as a YouTube
    description block (<stem>-chapters.txt).

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
        comp = doc["cards"][key]
        render(comps / f"{comp}.html", g / f"{comp}.mp4", "mp4", ["--quality", "high"])
    # chapters: one composition, many renders
    for c in doc["chapters"]:
        vars_ = json.dumps({"session": str(doc.get("session", "1")), "num": str(c["num"]), "title": c["title"]},
                           ensure_ascii=False)
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


# --------------------------------------------------------------------------- pieces
# The timeline is a list of PIECES, concatenated in order:
#   card    intro / outro (HyperFrames MP4 + silent audio)
#   keep    a source range, watermark + timed overlays baked in
#   freeze  a chapter break: the chapter's first frame held for `freeze` seconds,
#           silent, with the banner rising and holding over it
# A keep that contains a chapter point is split there: [in, at) | freeze | [at, out).
# The banner MOV is 3.1 s: [0, freeze) plays over the freeze piece, the rest --
# the drop-out -- over the first half-second of the resumed footage.

def pieces(doc):
    out = [{"name": "intro", "kind": "card"}]
    chapters = sorted(doc["chapters"], key=lambda c: c["at"])
    for k in doc["keeps"]:
        cuts = [c for c in chapters if k["in"] <= c["at"] < k["out"]]
        # boundaries: keep start, every chapter point, keep end -> consecutive keep pieces
        bounds = [k["in"], *(c["at"] for c in cuts), k["out"]]
        part = 0
        for i in range(len(bounds) - 1):
            b0, b1 = bounds[i], bounds[i + 1]
            if b1 - b0 <= 0.04:                     # chapter at the very start: no lead-in piece
                continue
            ch = next((c for c in cuts if c["at"] == b0), None)
            overlays = []
            if ch:
                out.append({"name": f"ch{ch['num']}", "kind": "freeze", "at": ch["at"], "dur": ch["freeze"],
                            "title": ch["title"], "num": ch["num"],
                            "overlays": [(0.0, ch["freeze"], f"ch{ch['num']}.mov", 0.0)]})
                # the resumed footage carries the banner's drop-out
                overlays.append((0.0, ch["dur"] - ch["freeze"], f"ch{ch['num']}.mov", ch["freeze"]))
            name = k["id"] if not cuts else f"{k['id']}{'abcdef'[part]}"
            out.append({"name": name, "kind": "keep", "in": b0, "out": b1, "note": k["note"], "overlays": overlays})
            part += 1
    # callouts go into whichever keep piece contains them: (local, dur, file, ss-into-file)
    for c in doc["callouts"]:
        for pc in out:
            if pc["kind"] == "keep" and pc["in"] <= c["at"] < pc["out"]:
                pc["overlays"].append((c["at"] - pc["in"], c["dur"], f"{c['id']}.mov", 0.0))
                break
        else:
            sys.exit(f"callout {c['id']} at {fmt(c['at'])} is not inside any keep")
    out.append({"name": "outro", "kind": "card"})
    return out


def _overlay_chain(cmd, overlays, g: Path, first_index: int):
    """Append overlay inputs to cmd; return the filter steps and the last label."""
    for local, dur, name, ss in overlays:
        cmd += ["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-itsoffset", f"{local:.3f}", "-i", str(g / name)]
    steps, last = [], "v0"
    for i, (local, dur, _, _) in enumerate(overlays):
        nxt = f"v{i + 1}"
        steps.append(f"[{last}][{first_index + i}:v]overlay=0:0:eof_action=pass:"
                     f"enable='between(t,{local:.3f},{local + dur:.3f})'[{nxt}]")
        last = nxt
    return steps, last


def keep_cmd(doc, pc, src: Path, g: Path, target: Path, draft: bool):
    length = round(pc["out"] - pc["in"], 3)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y",
           "-ss", f"{pc['in']:.3f}", "-t", f"{length:.3f}", "-i", str(src),
           "-i", str(g / "watermark.png")]
    steps, last = _overlay_chain(cmd, sorted(pc["overlays"]), g, 2)
    chain = ["[0:v][1:v]overlay=0:0[v0]", *steps]
    if draft:
        chain.append(f"[{last}]scale=960:-2[vout]"); last = "vout"
    a = doc["audio"]
    chain.append(f"[0:a]volume={a['gain_db']}dB,alimiter=limit={a['limit']}:attack=5:release=50,"
                 f"afade=t=in:st=0:d=0.05,afade=t=out:st={max(length - 0.05, 0):.3f}:d=0.05,"
                 f"apad=whole_dur={length:.3f}[aout]")   # audio exactly as long as the video: no gap at the seam
    cmd += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "[aout]",
            *(VIDEO_DRAFT if draft else VIDEO_FINAL), "-r", str(doc["fps"]), *AUDIO,
            "-f", "mpegts", str(target)]
    return cmd


def freeze_cmd(doc, pc, src: Path, g: Path, frames: Path, target: Path, draft: bool):
    """Hold the chapter's first frame, silent, with the banner rising over it."""
    frame = frames / f"{pc['name']}.png"
    if not frame.exists():
        run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", f"{pc['at']:.3f}", "-i", str(src),
             "-frames:v", "1", str(frame)])
    length = pc["dur"]
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y",
           "-loop", "1", "-framerate", str(doc["fps"]), "-t", f"{length:.3f}", "-i", str(frame),
           "-i", str(g / "watermark.png"),
           "-f", "lavfi", "-t", f"{length:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    steps, last = _overlay_chain(cmd, pc["overlays"], g, 3)
    chain = ["[0:v][1:v]overlay=0:0[v0]", *steps]
    if draft:
        chain.append(f"[{last}]scale=960:-2[vout]"); last = "vout"
    cmd += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "2:a",
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


def write_chapters(doc, marks, final: Path, out: Path, stem: str):
    """Embed MP4 chapter atoms (VLC, IINA, mpv, QuickTime show them) and write the
    YouTube description block -- YouTube reads chapters from the description, not
    from the file. First line must be 00:00 and each chapter >= 10 s."""
    total = duration(final)
    meta = [";FFMETADATA1"]
    bounds = [(0.0, "Intro")] + marks
    for i, (t, title) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else total
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(t * 1000)}", f"END={int(end * 1000)}", f"title={title}"]
    mfile = out / f"{stem}-chapters.ffmeta"
    mfile.write_text("\n".join(meta) + "\n")
    tmp = final.with_suffix(".chap.mp4")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(final), "-i", str(mfile),
         "-map_metadata", "1", "-map", "0", "-c", "copy", "-movflags", "+faststart", str(tmp)],
        out / "logs" / f"chapters-{stem}.log")
    tmp.replace(final)
    def yt(t): 
        t = int(t); return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"
    lines = [f"{yt(t)} {title}" for t, title in bounds]
    (out / f"{stem}-chapters.txt").write_text("\n".join(lines) + "\n")
    return lines


def build(doc, out: Path, draft: bool, only: str | None, keep_segments: bool, workers: int):
    src = ROOT / doc["source"]
    g = out / "graphics"
    stem = doc.get("stem", "S1")
    frames = out / f"frames-{stem}"; frames.mkdir(parents=True, exist_ok=True)
    seg = out / (f"segments-{stem}-draft" if draft else f"segments-{stem}")
    seg.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    plan = pieces(doc)
    jobs = []
    for pc in plan:
        t = seg / f"{pc['name']}.ts"
        if only and not pc["name"].startswith(only):
            continue
        if keep_segments and t.exists():
            continue
        if pc["kind"] == "card":
            jobs.append((pc["name"], card_cmd(doc, g / f"{doc['cards'][pc['name']]}.mp4", t, draft)))
        elif pc["kind"] == "freeze":
            jobs.append((pc["name"], freeze_cmd(doc, pc, src, g, frames, t, draft)))
        else:
            jobs.append((pc["name"], keep_cmd(doc, pc, src, g, t, draft)))

    print(f"{len(jobs)} ffmpeg jobs, {workers} at a time ({'draft' if draft else 'final'})")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run, cmd, out / "logs" / f"{name}{'-draft' if draft else ''}.log"): name for name, cmd in jobs}
        for f in as_completed(futs):
            name = futs[f]
            f.result()  # raises with the ffmpeg tail on failure
            print(f"  done {name:<6} {time.time() - t0:5.0f}s")

    order = [seg / f"{pc['name']}.ts" for pc in plan]
    missing = [p.name for p in order if not p.exists()]
    if missing:
        sys.exit(f"cannot concat, missing: {missing}")
    lst = seg / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in order))
    final = out / (f"{stem}-draft.mp4" if draft else f"{stem}-compact.mp4")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart", str(final)],
        out / "logs" / f"concat{'-draft' if draft else ''}.log")

    # output-time map, chapter marks, and the length check
    durs = {pc["name"]: duration(seg / f"{pc['name']}.ts") for pc in plan}
    expected = sum(durs.values())
    offset, rows, marks = 0.0, [], []
    for pc in plan:
        if pc["kind"] == "keep":
            rows.append((offset, f"{pc['name']:<5} {fmt(pc['in'])}-{fmt(pc['out'])}  {pc['note'][:58]}"))
            for local, dur, name, ss in pc["overlays"]:
                if ss == 0.0 and not name.startswith("ch"):
                    rows.append((offset + local, f"      callout {name[:-4]}"))
        elif pc["kind"] == "freeze":
            rows.append((offset, f"      >> chapter {pc['num']}: {pc['title']}  (freeze {pc['dur']}s @ source {fmt(pc['at'])})"))
            marks.append((offset, pc["title"]))
        else:
            rows.append((offset, pc["name"]))
        offset += durs[pc["name"]]
    yt = write_chapters(doc, marks, final, out, stem + ("-draft" if draft else ""))
    actual = duration(final)
    print(f"\n{final.name}: {fmt(actual)}  (pieces sum to {fmt(expected)}, "
          f"{'OK' if abs(actual - expected) < 0.5 else 'MISMATCH'})  {final.stat().st_size / 1e6:.0f} MB")
    print("\noutput-time map:")
    for t, label in rows:
        print(f"  {fmt(t)}  {label}")
    print(f"\nchapters (embedded in the MP4; paste into the YouTube description):")
    for line in yt:
        print(f"  {line}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cuts")
    ap.add_argument("stage", choices=["graphics", "draft", "final", "all"])
    ap.add_argument("--only", help="rebuild pieces whose name starts with this: K5, ch3, intro")
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
