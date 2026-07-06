"""Build the workshop demo: a captioned screenshot series + an MP4 walkthrough.

Regenerable, no screen recording (the reference build's pattern). Reads captured
assets from workshop/demo/assets/ and composes clean 1920x1080 frames:

  - a title card and an end card
  - "terminal" cards that render REAL captured command output
  - "browser" cards that embed REAL portal screenshots
  - a caption banner on every frame saying what the step does

Then stitches the frames into demo.mp4 with ffmpeg (one frame held N seconds).

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


def font(path, size):
    return ImageFont.truetype(path, size)


F_TITLE = font(SANS, 84)
F_SUB = font(SANS, 40)
F_CAP = font(SANS, 46)
F_STEP = font(SANS, 30)
F_MONO = font(MONO, 26)
F_MONO_S = font(MONO, 22)
F_FOOT = font(SANS, 28)


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
    d.text((70, H - 52), "Banking Analytics with AI Agents  ·  github.com/aayancheng/banking-analytics-workshop",
           font=F_FOOT, fill=MUTED)
    return img


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
    """Embed a portal screenshot inside a browser-chrome frame."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 90, 214, W - 90, H - 90
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(30, 40, 56))
    # chrome bar
    d.rounded_rectangle([x0, y0, x1, y0 + 52], radius=16, fill=(46, 58, 78))
    d.rectangle([x0, y0 + 34, x1, y0 + 52], fill=(46, 58, 78))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 24 + i * 28, y0 + 18, x0 + 40 + i * 28, y0 + 34], fill=c)
    d.rounded_rectangle([x0 + 150, y0 + 12, x0 + 640, y0 + 40], radius=14, fill=(28, 36, 50))
    d.text((x0 + 170, y0 + 16), "localhost:8100  ·  forwarded from your Codespace",
           font=F_MONO_S, fill=MUTED)

    shot = Image.open(shot_path).convert("RGB")
    avail_w, avail_h = (x1 - x0 - 4), (y1 - (y0 + 52) - 4)
    scale = min(avail_w / shot.width, avail_h / shot.height)
    nw, nh = int(shot.width * scale), int(shot.height * scale)
    shot = shot.resize((nw, nh), Image.LANCZOS)
    px = x0 + 2 + (avail_w - nw) // 2
    py = y0 + 54
    img.paste(shot, (px, py))


def title_card() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H // 2 + 130, W, H // 2 + 138], fill=ACCENT)
    d.text((W // 2, H // 2 - 120), "Banking Analytics with AI Agents",
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

    seq.append((codespaces_card(
        "Setup — open the repo in GitHub Codespaces. Nothing to install locally.",
        "GETTING STARTED"), 5.0))

    img = base("SESSION 1  ·  DATA", "Generate & audit a synthetic SME loan portfolio — seeded, leakage-safe.")
    terminal_card(img, read_lines("s1_data.txt", 16), ["make data", "python verify.py"])
    seq.append((img, 5.0))

    img = base("SESSION 2  ·  THE SCORE", "Train a WoE scorecard — it passes a hard AUC gate, or it doesn't ship.")
    terminal_card(img, read_lines("s2_train.txt", 16), ["make train-score", "python verify.py"])
    seq.append((img, 5.0))

    img = base("SESSION 3  ·  DECISIONS",
               "Adjudication + pricing on your score — the engine finds $1.28B mispriced.",
               "make train-adjudication · make price · make run  ->  http://localhost:8100")
    browser_card(img, ASSETS / "s3_portal.png")
    seq.append((img, 5.5))

    img = base("SESSION 4  ·  THE PORTFOLIO",
               "Early warning + proactive line increases, behind one portal.",
               "make train-ews · make train-line-increase  ->  watchlist + growth offers")
    browser_card(img, ASSETS / "s4_portal.png")
    seq.append((img, 5.5))

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


def build_video(frames: list[tuple[Path, float]]):
    concat = FRAMES / "concat.txt"
    lines = []
    for p, secs in frames:
        lines.append(f"file '{p.name}'")
        lines.append(f"duration {secs}")
    lines.append(f"file '{frames[-1][0].name}'")  # last frame needs a final entry
    concat.write_text("\n".join(lines))
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-movflags", "+faststart", str(OUT),
    ]
    subprocess.run(cmd, check=True, cwd=str(FRAMES),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    frames = build_frames()
    print(f"wrote {len(frames)} frames to {FRAMES.relative_to(HERE.parent.parent)}")
    build_video(frames)
    print(f"wrote {OUT.relative_to(HERE.parent.parent)}")
