# From live recordings to a mini online course

**Facilitator notes. Not student-facing.**

## When to buy Zoom Pro: September 9

The five sessions span **28 days** (Sep 10 → Oct 8). A monthly cycle is longer than that, so
**one month covers the whole pilot** if the start date is right:

| Subscribe | Renews | All 5 covered? | Idle before S1 |
|---|---|---|---|
| Sep 8 | Oct 8 | **no** — renewal lands *on* the last session | 2 days |
| **Sep 9** | **Oct 9** | **yes**, 1 day of margin | **1 day** |
| Sep 10 | Oct 10 | yes, 2 days of margin | 0 days |

**Sep 9, then immediately turn off auto-renew.** Cancelling a monthly plan stops the renewal
but keeps access to the end of the paid term — so doing it on day one means one charge
(~$17, not the $34 for two months) and nothing to remember on Oct 8. Confirm the renewal
date Zoom shows at checkout before relying on this; if it says Oct 8 rather than Oct 9, move
the purchase a day later.

Sep 10 also works and has more margin, but leaves no room to fix a settings problem.

> **This is a reason to lock the dates at Session 1.** One month only works if the five
> sessions stay weekly. Any slip past Oct 9 costs a second month.

### Sep 9, same day — a 20-minute Zoom-specific check
Dry run B doesn't need Zoom (it's you, a clock, and the run of show). But these settings do
need testing on the real product before Sep 10:

- [ ] Settings → Recording → **Record separate audio file for each participant**
- [ ] Settings → Recording → **Optimize for 3rd party video editor**
- [ ] **Record video during screen sharing** + **Place video next to shared screen**
- [ ] Record **locally**, not to the cloud — Pro's 10 GB of cloud storage is about two
      sessions, and cloud mode is the one that *doesn't* give per-speaker audio
- [ ] Start a meeting, record 3 minutes, confirm the per-participant files appear on disk
- [ ] Confirm the 40-minute banner is gone

---

## The part that happens during the sessions, not after

Three habits from Sep 10. Skip them and you face 7.5 hours of cold footage in November.

1. **Repeat every question before answering it.** You're already doing this for audio reasons.
   It has a second payoff: the question then exists *in your voice*, so a clip containing it
   needs nobody's permission. This is the single cheapest thing you can do to make the footage
   publishable.
2. **Write the cut list the same week.** Right after each session, scrub the recording once and
   note timestamps: what landed, what to re-record, where you fumbled. Ten minutes while it's
   fresh replaces an afternoon of hunting later.
3. **Re-record the known-bad bits immediately**, while the material is still loaded in your
   head. You already have the rig — the narration pipeline in `workshop/demo/` normalises to
   −16 LUFS and you know it works.

**Consent shortcut: build the course from your screen and your voice only.** With that rule,
you never need a release from anyone, and the awkward "can I use your face" email never gets
sent. Participant audio is still worth capturing — it tells you where people got stuck, which
is what you'll rewrite around — but it doesn't have to ship.

---

## Zoom settings that decide whether the footage is usable

Beyond the three in [online-delivery.md](online-delivery.md) (local recording, per-participant
audio, optimize for 3rd-party editor), four settings change what you can do afterwards. All are
in the **web portal → Settings → Recording**, and all must be on **before** the session — none
can be applied to footage you already have.

**1 · Record active speaker, gallery view and shared screen separately.** The single most
valuable one. It writes an extra `shared_screen` MP4 with **no webcam picture-in-picture burned
into it**. In the dry run your camera sat over the top-right of VS Code; in a composited file
those pixels are gone for good, and that corner is where tab bars and window controls live. With
the separate file you choose per-lecture whether your face appears at all.

**2 · "Display participants' names in the recording" — turn OFF.** Names burned into video
cannot be removed later. With ~40 bank practitioners, that is both a consent problem and an
irreversible one: if somebody asks to be taken out of a clip in October, the answer with names
burned in is "I can't."

**3 · "Ask participants for consent when a recording starts" — turn ON.** It puts a consent
prompt in front of every attendee at the moment recording begins, and the participation log
records it. That is the auditable half of the consent plan; the spoken notice at 0:00 is the
human half. Publishing clips of identifiable employees of named institutions — and CIBC, FNBO,
Milliman and BDC addresses are in this cohort — is exactly where you want a record.

**4 · Auto-save chat.** Chat is where the questions will be, and questions are the syllabus for
the re-recorded version. Save it, mine it, do not publish it — it carries names.

Also worth setting: background noise suppression to **Auto** (High can clip consonants on a
quiet voice), and timestamps on recordings **off** — they look like surveillance footage.

---

## If the destination is Udemy

The technical bar is low but two of its four requirements catch Zoom recordings specifically.

| Requirement | Where Zoom trips you |
|---|---|
| **720p minimum, 16:9** | Fine — record at 1920×1080 as the dry-run protocol already says |
| **Audio in BOTH channels** | ⚠️ Per-participant tracks are **mono**. A mono track that lands on one side is a standard rejection |
| **30+ minutes total** | Not a constraint; you will have ~7.5 hours of raw |
| **Custom, dynamic visuals** | Your portal, charts and notebook clear this easily; a static terminal for 20 minutes would not |

**The stereo gotcha, concretely.** Before submitting anything, force dual-mono:

```bash
ffmpeg -i lecture.mp4 -af "pan=stereo|c0=c0|c1=c0" -c:v copy lecture-stereo.mp4
```

Check it landed:

```bash
ffprobe -v error -show_entries stream=channels,channel_layout -of default=nw=1 lecture-stereo.mp4
```

**Two things you already have that most first-time instructors do not:**

- **A promo video.** `workshop/demo/demo.mp4` — 121 seconds, narrated, showing the finished
  platform. That is exactly the asset Udemy asks for and it is already built.
- **A completion check.** Almost no course can verify a student actually did the work. Yours ends
  every module on `python verify.py` and a green line. Lead the sales page with that rather than
  with hours of content — it is the only genuinely unusual thing about the course.

**Captions.** YouTube auto-generates and is fine for highlights. For Udemy, generate them
properly and edit — Whisper runs locally and free, no subscription:

```bash
pip install openai-whisper && whisper lecture.mp4 --model small --output_format srt
```

**The clean-take habit, worth ten minutes a week.** Immediately after each session, while the
material is still loaded, record one solo pass of that night's key demo — no interruptions, no
"can everyone see my screen", no waiting for stragglers. Five of those become five course
lectures, and they will beat any live capture. The live recording is then only for the cohort
and for highlights, which is all it was ever good for.

---

## Raw sessions are not a course

You'll finish Oct 8 with ~7.5 hours containing setup time, "can everyone see my screen",
cohort-specific asides and silences while people type. Nobody completes that.

**Target: ~3 hours, five modules, lessons of 4–8 minutes.** One lesson = one idea that ends
with something working. Ruthless subtraction is the whole job — most of what you cut is dead
air and cohort chatter, not teaching.

**The repo already is the course spine.** Stages 0–5 give you module boundaries with a
built-in completion check, which is the differentiator: almost no online course can verify
that a student actually did the thing. Every lesson can end on `python verify.py` and a green
line. Lead the sales page with that, not with hours of content.

**Structure per module:** the live explanation (cut from the recording) → the demo (cut, or
re-recorded clean) → the lab as a written exercise → the checkpoint. Slides, labs and prompt
cards already exist; only the video needs making.

### Tooling
- **Rough cuts:** `ffmpeg -ss/-to -c copy` is lossless and instant for lifting segments.
- **Real editing:** DaVinci Resolve (free) for anything needing transitions or multi-track.
- **Audio:** normalise every finished lesson the same way you normalised the narration —
  `loudnorm=I=-16:TP=-1.5:LRA=11`, verified with `ebur128`.
- **Don't buy a course platform before you have buyers.** An unlisted YouTube playlist, the
  public repo, and one landing page will carry the first cohort. Teachable/Podia when there's
  revenue to justify it.

### Sequence
1. **Oct 9–15** — cut Session 1 alone, publish it free as the taster. It doubles as the
   standalone Session 1 offer you were already considering.
2. **Feedback first.** The pilot's whole purpose is candid feedback; let it decide what gets
   rewritten before you cut four more modules around a structure that may change.
3. **Then modules 2–5**, one a week, re-recording rather than salvaging wherever the live take
   fights you. A clean solo re-take beats a rescued live one every time — and now costs you
   almost nothing, because the pipeline exists.
