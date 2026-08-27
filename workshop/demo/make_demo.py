"""Build the workshop demo: a captioned screenshot series + an MP4 walkthrough.

Regenerable, no screen recording (the reference build's pattern). Reads captured
assets from workshop/demo/assets/ and composes clean 1920x1080 frames:

  - a title card and an end card
  - "terminal" cards that render REAL captured command output
  - "browser" cards that embed REAL portal screenshots
  - a caption banner on every frame saying what the step does

Then stitches the frames into demo.mp4 with ffmpeg (one frame held N seconds).

If narration clips are present in audio/ (vo_00..vo_08, see NARRATION.md), the frame
timings come from the *recordings*: each frame is held for as long as its clip runs plus
a beat either side, or its storyboard seconds — whichever is longer. So a retake never
needs the timings re-tuned, the voice is never cut off mid-sentence, and a frame is never
whipped away before it can be read.

    python workshop/demo/make_demo.py         # writes frames/ + demo.mp4

Frames are also emitted as numbered PNGs so they double as a standalone
screenshot series for slides or a blog post.
"""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FRAMES = HERE / "frames"
OUT = HERE / "demo.mp4"
AUDIO = HERE / "audio"

# Narration padding, in seconds. LEAD/TAIL are the beats of silence around each clip so a
# frame never flips on the speaker's last syllable; END_HOLD keeps the closing card (and
# its URL) on screen after the final line lands.
LEAD_PAD = 0.35
TAIL_PAD = 0.75
END_HOLD = 1.5

W, H = 1920, 1080
# palette (matches the portal)
INK = (26, 35, 50)
NAVY = (16, 24, 38)
ACCENT = (36, 91, 178)
OK = (26, 127, 75)
WARN = (183, 121, 31)
BAD = (179, 55, 46)
PAPER = (246, 248, 251)
TERM_BG = (13, 20, 33)
TERM_FG = (222, 228, 236)
MUTED = (150, 162, 178)
WHITE = (255, 255, 255)

MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/Helvetica.ttc"
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
_EMOJI_FONT = ImageFont.truetype(EMOJI, 160)  # Apple Color Emoji has a strike at 160


def _emoji_glyph(char: str, target_h: int) -> Image.Image:
    """Render a color emoji to a cropped RGBA image scaled to target height."""
    tmp = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((16, 12), char, font=_EMOJI_FONT, embedded_color=True)
    box = tmp.getbbox()
    g = tmp.crop(box)
    scale = target_h / g.height
    return g.resize((max(1, int(g.width * scale)), target_h), Image.LANCZOS)


def paste_emoji(img: Image.Image, char: str, cx: int, cy: int, target_h: int):
    g = _emoji_glyph(char, target_h)
    img.paste(g, (int(cx - g.width / 2), int(cy - g.height / 2)), g)


def font(path, size):
    return ImageFont.truetype(path, size)


F_TITLE = font(SANS, 84)
F_SUB = font(SANS, 40)
F_CAP = font(SANS, 46)
F_STEP = font(SANS, 30)
F_MONO = font(MONO, 26)
F_MONO_S = font(MONO, 22)
F_FOOT = font(SANS, 28)
F_CARD_T = font(SANS, 42)
F_DESC = font(SANS, 29)
F_STRIP = font(SANS, 34)


def _wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def base(step_label: str, caption: str, cmd: str | None = None) -> Image.Image:
    """A frame with the top caption banner filled in. Content drawn by callers.
    Captions are kept to a single line by design (see the storyboard); `cmd` is an
    optional command hint drawn in the strip just below the banner."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # top banner
    d.rectangle([0, 0, W, 150], fill=INK)
    d.rectangle([0, 150, W, 156], fill=ACCENT)
    if step_label:
        d.text((70, 34), step_label, font=F_STEP, fill=(150, 180, 230))
    line = _wrap(d, caption, F_CAP, W - 140)[0]
    d.text((70, 78 if step_label else 52), line, font=F_CAP, fill=WHITE)
    if cmd:
        d.text((70, 168), cmd, font=F_STEP, fill=(96, 118, 150))
    # footer
    d.text((70, H - 52), "Credit Analytics with AI Agents  ·  github.com/aayancheng/banking-analytics-workshop",
           font=F_FOOT, fill=MUTED)
    return img


def figure_card(img: Image.Image, fig_path: Path):
    """Embed a generated figure (table/chart from capture_assets.py) on a clean
    panel — no browser chrome, because these are rendered outputs, not screenshots."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 90, 212, W - 90, H - 96
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=WHITE,
                        outline=(214, 222, 234), width=2)
    fig = Image.open(fig_path).convert("RGB")
    avail_w, avail_h = (x1 - x0 - 28), (y1 - y0 - 28)
    scale = min(avail_w / fig.width, avail_h / fig.height)
    nw, nh = int(fig.width * scale), int(fig.height * scale)
    fig = fig.resize((nw, nh), Image.LANCZOS)
    img.paste(fig, (x0 + 14 + (avail_w - nw) // 2, y0 + 14 + (avail_h - nh) // 2))


def terminal_card(img: Image.Image, lines: list[str], prompt_cmds: list[str] | None = None):
    """Draw a terminal window in the content area with the given output lines.
    prompt_cmds (if given) are shown at the top as typed `$ ` commands."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 90, 210, W - 90, H - 110
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=TERM_BG)
    # title bar + traffic lights
    d.rounded_rectangle([x0, y0, x1, y0 + 46], radius=16, fill=(32, 42, 58))
    d.rectangle([x0, y0 + 30, x1, y0 + 46], fill=(32, 42, 58))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 22 + i * 26, y0 + 15, x0 + 36 + i * 26, y0 + 29], fill=c)
    d.text((x0 + 130, y0 + 12), "bash — banking-analytics-workshop", font=F_MONO_S, fill=MUTED)

    ty = y0 + 74
    lh = 34
    if prompt_cmds:
        for cmd in prompt_cmds:
            d.text((x0 + 30, ty), "$ ", font=F_MONO, fill=(120, 220, 140))
            d.text((x0 + 30 + int(d.textlength("$ ", font=F_MONO)), ty), cmd,
                   font=F_MONO, fill=WHITE)
            ty += lh
        ty += 8
    for raw in lines:
        line = raw.rstrip("\n")
        color = TERM_FG
        if "✅" in line or "GATE PASS" in line or "green" in line or "OK" in line:
            color = (95, 224, 138)
        elif "❌" in line or "FAIL" in line:
            color = (255, 128, 120)
        elif line.strip().startswith("["):
            color = (150, 200, 255)
        # strip emoji that Menlo can't render; keep a text marker
        line = line.replace("✅", "OK  ").replace("❌", "X  ").replace("→", "->")
        d.text((x0 + 30, ty), line[:96], font=F_MONO, fill=color)
        ty += lh
        if ty > y1 - 40:
            break


def browser_card(img: Image.Image, shot_path: Path):
    """Embed a portal screenshot inside a browser-chrome frame.

    The window is sized to the screenshot so the chrome always hugs its content —
    otherwise a wide crop leaves an empty slab of chrome below the image."""
    shot = Image.open(shot_path).convert("RGB")
    max_w, max_h = W - 180, (H - 90) - (214 + 52)
    scale = min(max_w / shot.width, max_h / shot.height)
    nw, nh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((nw, nh), Image.LANCZOS)

    x0 = (W - (nw + 4)) // 2
    y0 = 214
    x1, y1 = x0 + nw + 4, y0 + 52 + nh + 2

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(30, 40, 56))
    # chrome bar
    d.rounded_rectangle([x0, y0, x1, y0 + 52], radius=16, fill=(46, 58, 78))
    d.rectangle([x0, y0 + 34, x1, y0 + 52], fill=(46, 58, 78))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 24 + i * 28, y0 + 18, x0 + 40 + i * 28, y0 + 34], fill=c)
    d.rounded_rectangle([x0 + 150, y0 + 12, x0 + 640, y0 + 40], radius=14, fill=(28, 36, 50))
    d.text((x0 + 170, y0 + 16), "localhost:8100  ·  forwarded from your Codespace",
           font=F_MONO_S, fill=MUTED)

    img.paste(shot, (x0 + 2, y0 + 52))


def title_card() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H // 2 + 130, W, H // 2 + 138], fill=ACCENT)
    d.text((W // 2, H // 2 - 120), "Credit Analytics with AI Agents",
           font=F_TITLE, fill=WHITE, anchor="mm")
    d.text((W // 2, H // 2 - 20), "A 5-session workshop you run in your browser",
           font=F_SUB, fill=(150, 180, 230), anchor="mm")
    d.text((W // 2, H // 2 + 200),
           "From setup to a defended lending platform — one command at every step",
           font=F_STEP, fill=MUTED, anchor="mm")
    d.text((W // 2, H // 2 + 260), "python verify.py  ->  \"you are here, and it works\"",
           font=font(MONO, 30), fill=(95, 224, 138), anchor="mm")
    return img


def codespaces_card(caption: str, step: str) -> Image.Image:
    """Synthesized 'Open in Codespaces' setup frame (the create screen is a GitHub
    UI we describe rather than screenshot, so the frame stays reproducible)."""
    img = base(step, caption)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 90, 210, W - 90, H - 110
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=WHITE, outline=(210, 218, 230), width=2)
    steps = [
        ("1", "On the repo, click  Code  >  Codespaces  >  Create codespace on main"),
        ("2", "The devcontainer builds and runs  make setup && make verify  for you"),
        ("3", "When the terminal shows the line below, you are ready — nothing to install"),
    ]
    yy = y0 + 70
    for n, tx in steps:
        d.ellipse([x0 + 60, yy, x0 + 104, yy + 44], fill=ACCENT)
        d.text((x0 + 82, yy + 22), n, font=F_STEP, fill=WHITE, anchor="mm")
        d.text((x0 + 130, yy + 6), tx, font=F_SUB, fill=INK)
        yy += 96
    # the verify-green strip
    yy += 12
    d.rounded_rectangle([x0 + 60, yy, x1 - 60, yy + 150], radius=12, fill=TERM_BG)
    d.text((x0 + 90, yy + 26), "$ python verify.py", font=F_MONO, fill=WHITE)
    d.text((x0 + 90, yy + 66), "[1/2] Python 3.11+ ............ OK", font=F_MONO, fill=(150, 200, 255))
    d.text((x0 + 90, yy + 100), "OK  Stage 0 verified — you are here, and it works.",
           font=F_MONO, fill=(95, 224, 138))
    return img


def overview_card() -> Image.Image:
    """Slide 2 — what you'll learn, for anyone, no code. Four moves + the
    transferability message."""
    img = base("BUSINESS ANALYTICS  ·  THE BIG PICTURE",
               "What you'll learn — the four moves behind every analytics decision.")
    d = ImageDraw.Draw(img)
    items = [
        ("\U0001F3E2", "Build the portfolio",
         "Create a realistic set of small-business borrowers to practice on — safe, made-up data."),
        ("\U0001F4CA", "Score the risk",
         "Develop a credit scorecard that tells safe borrowers from risky ones — with reasons."),
        ("⚖️", "Decide & price",
         "Turn each score into an approve or decline — and the right price for the risk taken."),
        ("\U0001F6A8", "Monitor & step in",
         "Watch the portfolio to catch loans going bad early — while there is still time to act."),
    ]
    cw, ch = 850, 318
    coords = [(90, 200), (980, 200), (90, 540), (980, 540)]
    for (x, y), (emo, title, desc), n in zip(coords, items, [1, 2, 3, 4]):
        d.rounded_rectangle([x, y, x + cw, y + ch], radius=18, fill=WHITE,
                            outline=(214, 222, 234), width=2)
        paste_emoji(img, emo, x + 118, y + ch // 2, 130)
        d.ellipse([x + 40, y + 34, x + 82, y + 76], outline=ACCENT, width=3)
        d.text((x + 61, y + 55), str(n), font=F_STEP, fill=ACCENT, anchor="mm")
        tx = y  # noqa: unused, keep flake quiet
        d.text((x + 218, y + 56), title, font=F_CARD_T, fill=INK)
        for i, line in enumerate(_wrap(d, desc, F_DESC, cw - 250)):
            d.text((x + 218, y + 128 + i * 42), line, font=F_DESC, fill=(70, 84, 104))

    # transferability strip
    sy = 892
    d.rounded_rectangle([90, sy, 1830, sy + 116], radius=16, fill=INK)
    d.text((124, sy + 20), "Learn it here on small-business lending —",
           font=F_STRIP, fill=WHITE)
    d.text((124, sy + 64),
           "then reuse the very same four moves for investing, marketing, fraud, and beyond.",
           font=F_STRIP, fill=(150, 200, 255))
    for i, emo in enumerate(("\U0001F4C8", "\U0001F6D2", "\U0001F6E1️")):
        paste_emoji(img, emo, 1560 + i * 90, sy + 58, 60)
    return img


def end_card() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.text((W // 2, H // 2 - 110), "Five sessions. Six checkpoints.",
           font=F_TITLE, fill=WHITE, anchor="mm")
    d.text((W // 2, H // 2 + 4), "You are here, and it all works.",
           font=F_SUB, fill=(95, 224, 138), anchor="mm")
    d.text((W // 2, H // 2 + 150),
           "github.com/aayancheng/banking-analytics-workshop",
           font=F_STEP, fill=(150, 180, 230), anchor="mm")
    d.text((W // 2, H // 2 + 210), "TeamYan  ·  teamyan.substack.com",
           font=F_FOOT, fill=MUTED, anchor="mm")
    return img


def read_lines(name: str, keep: int = 40) -> list[str]:
    p = ASSETS / name
    if not p.exists():
        return [f"(missing asset: {name})"]
    lines = [l for l in p.read_text().splitlines() if l.strip()
             and not l.startswith(".venv/bin/python")]  # drop Makefile recipe echoes
    return lines[-keep:]


# ---- the storyboard: (filename, seconds, builder) ----------------------------
def build_frames() -> list[tuple[Path, float]]:
    FRAMES.mkdir(exist_ok=True)
    seq: list[tuple[Image.Image, float]] = []

    seq.append((title_card(), 3.5))

    seq.append((overview_card(), 7.0))

    seq.append((codespaces_card(
        "Setup — open the repo in GitHub Codespaces. Nothing to install locally.",
        "GETTING STARTED"), 4.5))

    img = base("SESSION 1  ·  YOUR PORTFOLIO",
               "Build 12,000 SME borrowers — realistic enough to model, safe to publish.",
               "make data  ·  python verify.py  ->  Stage 1 verified")
    figure_card(img, ASSETS / "s1_portfolio.png")
    seq.append((img, 8.5))

    img = base("SESSION 2  ·  YOUR CREDIT SCORE",
               "Score every borrower 300–850 — and prove the score sorts good from bad.",
               "make train-score  ·  held-out AUC 0.8176  ·  gate >= 0.78  PASS")
    figure_card(img, ASSETS / "s2_score_distribution.png")
    seq.append((img, 8.5))

    img = base("SESSION 3  ·  DECISIONS",
               "Adjudication + pricing on your score — the engine finds $1.28B mispriced.",
               "make train-adjudication · make price · make run  ->  http://localhost:8100")
    browser_card(img, ASSETS / "s3_portal.png")
    seq.append((img, 5.5))

    img = base("SESSION 4  ·  YOUR WATCHLIST",
               "Catch trouble early — a ranked watchlist that names why, borrower by borrower.",
               "make train-ews  ·  python verify.py  ->  Stage 4 verified")
    browser_card(img, ASSETS / "s4_watchlist.png")
    seq.append((img, 9.0))

    img = base("SESSION 5  ·  GOVERNANCE", "Assemble the model documentation pack — nine checks green, demo-ready.")
    terminal_card(img, read_lines("s5_docpack.txt", 16), ["make docpack", "python verify.py"])
    seq.append((img, 5.0))

    seq.append((end_card(), 4.0))

    out: list[tuple[Path, float]] = []
    for i, (im, secs) in enumerate(seq):
        p = FRAMES / f"frame_{i:02d}.png"
        im.save(p)
        out.append((p, secs))
    return out


# ---- narration ---------------------------------------------------------------
def _ffmpeg(args: list[str], cwd: Path | None = None):
    """Run ffmpeg quietly, but surface its stderr when it fails — a silent
    CalledProcessError from a filtergraph typo costs an afternoon."""
    r = subprocess.run(["ffmpeg", "-y", "-nostdin", *args], cwd=cwd and str(cwd),
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")


def _duration(path: Path) -> float:
    """Measured, never assumed — loudnorm and container padding both move the number."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def narration_clips(n_frames: int) -> list[Path | None]:
    """audio/vo_00.* .. audio/vo_NN.*, index-aligned to the frames. Missing clips are
    None so a half-recorded voiceover still builds (those frames stay silent)."""
    clips: list[Path | None] = []
    for i in range(n_frames):
        found = None
        for ext in (".m4a", ".wav", ".mp3", ".aac", ".aiff"):
            cand = AUDIO / f"vo_{i:02d}{ext}"
            if cand.exists():
                found = cand
                break
        clips.append(found)
    return clips


def build_narration(clips: list[Path | None],
                    storyboard: list[float]) -> tuple[Path, list[float]]:
    """Compose one narration track and return it with the frame durations it implies.

    Each frame becomes  [lead silence][clip, cleaned][tail silence]  so the audio and the
    frame boundaries line up by construction rather than by hand-syncing. The storyboard
    seconds act as a floor on each frame, so a brisk take never robs a viewer of the time
    to read what is on screen. Every clip is normalised individually, so takes recorded on
    different days sit at the same level.
    Returns (narration.wav, per-frame seconds) — the seconds are *measured* off the
    rendered segments, so the track and the video cannot drift apart.
    """
    fmt = "aformat=sample_fmts=s16:sample_rates=48000:channel_layouts=mono"
    segs: list[Path] = []
    secs: list[float] = []
    work = FRAMES / "narration"
    work.mkdir(exist_ok=True)
    for i, (clip, story) in enumerate(zip(clips, storyboard)):
        seg = work / f"seg_{i:02d}.wav"
        if clip is None:
            _ffmpeg(["-f", "lavfi", "-t", f"{story}",
                     "-i", "anullsrc=r=48000:cl=mono", str(seg)])
        else:
            spoken = _duration(clip)
            # The storyboard second is a *read-time floor*, not a target: a frame showing
            # the S1 table or the S4 watchlist has to stay up long enough to be read, even
            # if the narrator covered it in four words. Voice can extend a frame, never
            # cut it short.
            tail = max(TAIL_PAD, story - LEAD_PAD - spoken)
            if i == len(clips) - 1:
                tail += END_HOLD
            # highpass kills desk/room rumble; loudnorm lands every clip on the same
            # perceived level. loudnorm resamples internally — hence the second aformat.
            _ffmpeg([
                "-f", "lavfi", "-t", f"{LEAD_PAD}", "-i", "anullsrc=r=48000:cl=mono",
                "-i", str(clip),
                "-f", "lavfi", "-t", f"{tail}", "-i", "anullsrc=r=48000:cl=mono",
                "-filter_complex",
                f"[1:a]{fmt},highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11,{fmt}[v];"
                f"[0:a][v][2:a]concat=n=3:v=0:a=1[out]",
                "-map", "[out]", str(seg),
            ])
        segs.append(seg)
        secs.append(_duration(seg))

    listing = work / "segs.txt"
    listing.write_text("\n".join(f"file '{s.name}'" for s in segs))
    narration = FRAMES / "narration.wav"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
             str(narration)], cwd=work)
    return narration, secs


def build_video(frames: list[tuple[Path, float]], narration: Path | None = None):
    concat = FRAMES / "concat.txt"
    lines = []
    for p, secs in frames:
        lines.append(f"file '{p.name}'")
        lines.append(f"duration {secs}")
    lines.append(f"file '{frames[-1][0].name}'")  # last frame needs a final entry
    concat.write_text("\n".join(lines))
    # -t pins the runtime to the storyboard: the repeated final entry above exists only so
    # the concat demuxer honours the last frame's duration, and would otherwise show the
    # end card twice.
    total = sum(secs for _, secs in frames)
    video = FRAMES / "silent.mp4" if narration else OUT
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-t", f"{total}",
             "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
             "-movflags", "+faststart", str(video)], cwd=FRAMES)
    if narration:
        _ffmpeg(["-i", str(video), "-i", str(narration), "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                 "-shortest", str(OUT)])


if __name__ == "__main__":
    frames = build_frames()
    print(f"wrote {len(frames)} frames to {FRAMES.relative_to(HERE.parent.parent)}")

    narration = None
    clips = narration_clips(len(frames))
    if any(c is not None for c in clips):
        narration, secs = build_narration(clips, [s for _, s in frames])
        frames = [(p, s) for (p, _), s in zip(frames, secs)]
        have = [f"{i:02d}" for i, c in enumerate(clips) if c is not None]
        print(f"narration: {len(have)}/{len(clips)} clips ({', '.join(have)})")
    else:
        print(f"narration: none found in {AUDIO.name}/ — building silent "
              f"(see {(HERE / 'NARRATION.md').name})")

    build_video(frames, narration)
    print(f"wrote {OUT.relative_to(HERE.parent.parent)} "
          f"({sum(s for _, s in frames):.1f}s)")
