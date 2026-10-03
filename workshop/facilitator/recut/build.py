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
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # repo root
HF = HERE / "hf"                # HyperFrames project
# the pin lives in hf/package.json (`npx hyperframes@latest upgrade --project hf` bumps it);
# read it from there so build.py and the project can never disagree on the version
_PIN = re.search(r'hyperframes@(\d+\.\d+\.\d+)', (HF / "package.json").read_text()).group(1)
HF_CLI = ["npx", "--yes", f"hyperframes@{_PIN}"]

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


def vduration(path: Path) -> float:
    """Length of the VIDEO stream. The container's duration (`duration()`) includes the audio's
    last padded AAC frame -- ~21 ms over per piece -- and the concat demuxer offsets each file
    by the container length, so a cut that must sit on a musical beat has to be timed by this."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip().splitlines()[0])


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
    shared = [f for f in (comps / "shared.css", comps / "shared.js", comps / "hook.css", comps / "hook.js") if f.exists()]

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
        if key in doc.get("cards", {}):
            comp = doc["cards"][key]
            render(comps / f"{comp}.html", g / f"{comp}.mp4", "mp4", ["--quality", "high"])
    # a cards-only sequence (the promo): each entry renders its composition, optionally with
    # variables, under its own name -- so a hook rendered at a whole number of bars for the
    # promo never overwrites the chapter video's render of the same composition
    for e in doc.get("sequence", []):
        comp, name = e["card"], e.get("as", e["card"])
        target = g / f"{name}.mp4"
        if e.get("vars"):
            vars_ = json.dumps(e["vars"], ensure_ascii=False)
            stamp = target.with_suffix(".vars")
            if stale(target, comps / f"{comp}.html") or not stamp.exists() or stamp.read_text() != vars_:
                target.unlink(missing_ok=True)
                render(comps / f"{comp}.html", target, "mp4", ["--quality", "high", "--variables", vars_])
                stamp.write_text(vars_)
            else:
                print(f"  up to date  {target.name}")
        else:
            render(comps / f"{comp}.html", target, "mp4", ["--quality", "high"])
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
    if doc.get("sequence"):
        return [{"name": e.get("as", e["card"]), "kind": "card", "comp": e.get("as", e["card"])} for e in doc["sequence"]]
    out = [{"name": "intro", "kind": "card", "comp": doc["cards"]["intro"]}]
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
            out.append({"name": name, "kind": "keep", "in": b0, "out": b1, "note": k["note"], "overlays": overlays,
                        "mark": k.get("mark") if part == 0 else None, "source": k.get("source"),
                        "gain_db": k.get("gain_db")})
            part += 1
    # callouts go into whichever keep piece contains them: (local, dur, file, ss-into-file)
    for c in doc["callouts"]:
        for pc in out:
            if pc["kind"] == "keep" and pc.get("source") == c.get("source") and pc["in"] <= c["at"] < pc["out"]:
                pc["overlays"].append((c["at"] - pc["in"], c["dur"], f"{c['id']}.mov", 0.0))
                break
        else:
            sys.exit(f"callout {c['id']} at {fmt(c['at'])} is not inside any keep")
    out.append({"name": "outro", "kind": "card", "comp": doc["cards"]["outro"]})
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


def _caption_list(doc, pc, g: Path, target: Path, length: float):
    """The piece's captions as an ffmpeg concat list of PNGs with durations (piece-local
    time), blank.png filling the gaps. None when the cuts file has no captions."""
    if not doc.get("captions"):
        return None
    cdir = g / f"{doc['stem'].split('-ch')[0]}-captions"
    segs = json.loads((cdir / "segments.json").read_text())
    src = pc.get("source")
    mine = sorted((max(s["start"], pc["in"]) - pc["in"], min(s["end"], pc["out"]) - pc["in"], s["png"])
                  for s in segs if s["source"] == src and s["end"] > pc["in"] and s["start"] < pc["out"])
    lines, t = [], 0.0
    for a, b, png in mine:
        if a > t + 0.001:
            lines += [f"file '{(cdir / 'blank.png').resolve()}'", f"duration {a - t:.3f}"]
        lines += [f"file '{(cdir / png).resolve()}'", f"duration {b - a:.3f}"]
        t = b
    if length > t + 0.001:
        lines += [f"file '{(cdir / 'blank.png').resolve()}'", f"duration {length - t:.3f}"]
    lines.append(f"file '{(cdir / 'blank.png').resolve()}'")      # the concat demuxer drops the last duration
    path = target.with_suffix(".captions.txt")
    path.write_text("\n".join(lines) + "\n")
    return path


def keep_cmd(doc, pc, src: Path, g: Path, target: Path, draft: bool):
    # a keep may name its own source -- a pickup recorded after the session (S3's P1-P3)
    src = ROOT / pc["source"] if pc.get("source") else src
    length = round(pc["out"] - pc["in"], 3)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y",
           "-ss", f"{pc['in']:.3f}", "-t", f"{length:.3f}", "-i", str(src),
           "-i", str(g / "watermark.png")]
    steps, last = _overlay_chain(cmd, sorted(pc["overlays"]), g, 2)
    chain = ["[0:v][1:v]overlay=0:0[v0]", *steps]
    caps = _caption_list(doc, pc, g, target, length)
    if caps:                                  # burned-in captions (captions.py): one timed image list
        idx = 2 + len(pc["overlays"])
        cmd += ["-f", "concat", "-safe", "0", "-i", str(caps)]
        chain.append(f"[{last}][{idx}:v]overlay=0:0:eof_action=pass[vcap]"); last = "vcap"
    if draft:
        chain.append(f"[{last}]scale=960:-2[vout]"); last = "vout"
    a = doc["audio"]
    gain = a["gain_db"] + (pc.get("gain_db") or 0.0)   # a pickup recorded closer to the mic sits a little hot
    chain.append(f"[0:a]volume={gain}dB,alimiter=limit={a['limit']}:attack=5:release=50,"
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


def loudness(path: Path):
    """Integrated loudness, range and true peak of a file's audio (ffmpeg ebur128)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    vals = {}
    for key, label in (("I", "I:"), ("LRA", "LRA:"), ("TP", "Peak:")):
        m = re.search(re.escape(label) + r"\s*([-\d.]+)", tail)
        vals[key] = float(m.group(1)) if m else float("nan")
    return vals


def mix_music(doc, final: Path, out: Path):
    """Lay a music bed and timed SFX under the concatenated video, at a target loudness.

    `music`: {"file", "fade_in", "fade_out", "lufs", "true_peak", "sfx": [{"file", "at", "peak",
    "gain_db"}]}. `at` is the OUTPUT second at which the sound's peak should land and `peak` is
    where that peak sits inside the file, so the file starts at at - peak. Two passes: the mix
    is measured at its authored levels, then one global gain moves it to `lufs` and a limiter
    holds `true_peak`. The video is stream-copied; the cards' silent audio is dropped."""
    m = doc["music"]
    length = vduration(final)
    music = ROOT / m["file"]
    fi, fo = m.get("fade_in", 0.5), m.get("fade_out", 2.5)
    sfx = m.get("sfx", [])
    cmd_in = ["-i", str(final), "-i", str(music)]
    chain = [f"[1:a]atrim=0:{length:.3f},asetpts=PTS-STARTPTS,"
             f"afade=t=in:st=0:d={fi},afade=t=out:st={max(length - fo, 0):.3f}:d={fo}[bed]"]
    labels = ["[bed]"]
    for i, e in enumerate(sfx):
        cmd_in += ["-i", str(ROOT / e["file"])]
        delay = max(int(round((e["at"] - e.get("peak", 0.0)) * 1000)), 0)
        chain.append(f"[{2 + i}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={e.get('gain_db', -18)}dB,"
                     f"adelay={delay}|{delay}[s{i}]")
        labels.append(f"[s{i}]")
    mix = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0"

    def render_audio(gain_db: float, target: Path, video: bool):
        fc = ";".join(chain + [f"{mix},volume={gain_db:.2f}dB,alimiter=limit={m.get('limit', 0.89)}:attack=5:release=50,"
                                f"apad=whole_dur={length:.3f}[aout]"])
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", *cmd_in, "-filter_complex", fc]
        if video:
            cmd += ["-map", "0:v", "-map", "[aout]", "-map_metadata", "0", "-map_chapters", "0", "-c:v", "copy",
                    *AUDIO, "-t", f"{length:.3f}", "-movflags", "+faststart", str(target)]
        else:
            cmd += ["-map", "[aout]", "-t", f"{length:.3f}", "-c:a", "pcm_s16le", "-ar", "48000", str(target)]
        run(cmd, out / "logs" / f"music-{target.stem}.log")

    probe = out / "logs" / f"{final.stem}-mix-probe.wav"
    render_audio(0.0, probe, video=False)
    before = loudness(probe)
    gain = m.get("lufs", -14.0) - before["I"]
    tmp = final.with_suffix(".mix.mp4")
    render_audio(gain, tmp, video=True)
    tmp.replace(final)
    probe.unlink(missing_ok=True)
    after = loudness(final)
    print(f"\nmusic: {music.name}  fade {fi}s/{fo}s  {len(sfx)} sfx  gain {gain:+.1f} dB  "
          f"-> {after['I']:.1f} LUFS (target {m.get('lufs', -14.0)}), LRA {after['LRA']:.1f}, true peak {after['TP']:.1f} dBTP")
    for e in sfx:
        print(f"  sfx {fmt(e['at'])}  {Path(e['file']).stem:<16} {e.get('gain_db', -18):+.0f} dB")


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
    src = ROOT / doc["source"] if doc.get("source") else None
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
            jobs.append((pc["name"], card_cmd(doc, g / f"{pc['comp']}.mp4", t, draft)))
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
    final = out / (f"{stem}-draft.mp4" if draft else f"{stem}-compact.mp4")
    if doc.get("music"):
        # a music build is cut on beats: tell the demuxer each piece's exact video length so no
        # seam inherits the audio's 21 ms padding, and drop the cards' silent audio here -- the
        # bed replaces it in mix_music()
        lst.write_text("".join(f"file '{p.resolve()}'\nduration {vduration(p):.3f}\n" for p in order))
        run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-an", "-c:v", "copy", "-movflags", "+faststart", str(final)],
            out / "logs" / f"concat{'-draft' if draft else ''}.log")
        durs = {pc["name"]: vduration(seg / f"{pc['name']}.ts") for pc in plan}
    else:
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in order))
        run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart", str(final)],
            out / "logs" / f"concat{'-draft' if draft else ''}.log")
        durs = {pc["name"]: duration(seg / f"{pc['name']}.ts") for pc in plan}

    # output-time map, chapter marks, and the length check
    expected = sum(durs.values())
    offset, rows, marks = 0.0, [], []
    for pc in plan:
        if pc["kind"] == "keep":
            rows.append((offset, f"{pc['name']:<5} {fmt(pc['in'])}-{fmt(pc['out'])}  {pc['note'][:58]}"))
            if pc.get("mark") and not doc["chapters"]:
                # a keep-level chapter mark: a YouTube chapter without a freeze. Only in a cuts file
                # with no chapter freezes (the per-chapter videos) -- in the stitched version the
                # freeze is the mark, and a second one two seconds later breaks YouTube's 10 s rule.
                marks.append((offset, pc["mark"]))
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
    if doc.get("music"):
        mix_music(doc, final, out)
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
