# Confirmation email — pilot cohort

**Facilitator notes. Not student-facing.** Template: no names, no live links.

**Send:** individually, not as a group thread or BCC blast. Four people; personal beats
efficient, and a reply is the goal.

**Fill in before sending:** `{{FIRST_NAME}}`, `[[MEETING_LINK_1]]`, `[[MEETING_LINK_2]]`.
**Attach:** `workshop/facilitator/credit-analytics-workshop.ics` (all five sessions; it
renders in the recipient's own time zone, so nobody does the arithmetic).

**Hong Kong recipients:** change the subject line to *"…starts Friday Sep 11, 8:00am HK"* —
their calendar day differs from the one in the table's first column, and the subject is the
part people skim. The `.ics` already carries a 12-hour alarm, which lands the evening before
for HK.

**Then diarise:** a short reminder the morning of *their* Sep 11.

---

## Subject

> You're in — Credit Analytics with AI Agents starts Thursday Sep 10

*(HK variant: "You're in — Credit Analytics with AI Agents starts Friday Sep 11, 8:00am HK")*

---

## Body

Hi {{FIRST_NAME}},

You're confirmed for the pilot cohort of **Credit Analytics with AI Agents** — five sessions,
90 minutes each, free.

Hong Kong attends on the **following calendar day**, so both columns are below:

| Session | Toronto (EDT) | Hong Kong (HKT) |
|---|---|---|
| **S1** — How a Bank Decides | Thu **Sep 10**, 8:00–9:30pm | Fri **Sep 11**, 8:00–9:30am |
| **S2** — The Score Spine | Thu Sep 17, 8:00–9:30pm | Fri Sep 18, 8:00–9:30am |
| **S3** — Adjudication & Pricing | Thu Sep 24, 8:00–9:30pm | Fri Sep 25, 8:00–9:30am |
| **S4** — The Portfolio Wakes Up | Thu Oct 1, 8:00–9:30pm | Fri Oct 2, 8:00–9:30am |
| **S5** — Governance & Defence | Thu Oct 8, 8:00–9:30pm | Fri Oct 9, 8:00–9:30am |

I've attached a calendar file with all five. It'll land in your own time zone, so you don't
have to do the maths.

**Join:** [[MEETING_LINK_1]]
We take a five-minute break about 45 minutes in, and the second half uses a different link:
[[MEETING_LINK_2]] — both are in the calendar invite too.

---

### One thing to do before Sep 10 — about 10 minutes

Please get a green check *before* the session:

1. Go to **github.com/aayancheng/banking-analytics-workshop**
2. Click **Code → Codespaces → Create codespace on main**
3. Wait for it to build, then run: `python verify.py`
4. You're looking for: **✅ Stage 0 verified — you are here, and it works.**

That's the entire setup. Nothing installs on your laptop, and it runs the same whether
you're on a Mac, a PC, or a locked-down work machine.

If it doesn't go green, reply and send me what you see. I'd much rather fix it this week
than spend our 90 minutes on it.

### What Session 1 actually is

You'll build a portfolio of 12,000 small-business borrowers, see exactly how that data is
generated — and then deliberately poison it. We'll train a model on a column you're not
allowed to use, watch the AUC go to ~1.0, and sit with why that number is worthless.

The point isn't the model. It's that leakage is a **control** problem, not a modelling
problem, and controls belong in code where someone can review them.

You'll leave with checkpoint `stage-1` on your machine and one command that proves it works.

### A few practical things

- **Every session is recorded**, and the recording goes to the cohort afterwards. Missing a
  week genuinely costs you nothing — each checkpoint is self-sufficient, so you can jump
  straight to where the group is and everything before it is already built and working.
- **I may publish short clips publicly** (YouTube, my newsletter). Your camera and mic are
  entirely your choice — keep them off and you won't be in the recording. If a clip does
  include you, your voice, or your employer, I'll ask you first, in writing, before it goes
  anywhere.
- Bring questions. Four people is small enough that this can be a conversation, and I'd
  rather it were one.

### One ask

Hit reply with a single line: **what's the one thing you want to be able to do at the end of
five weeks?** This is a pilot — I'll shape the sessions around what comes back, and yours is
one of four voices, so it counts for a lot.

See you on the 10th.

Yan

---

## Why it's built this way

- **The pre-work ask is the real payload.** At 90 minutes there is no room for a setup sweep,
  and `stage-0` exists precisely so it can happen beforehand. It's stated as a 10-minute task
  with a specific success string, not "please get set up".
- **The consent language is deliberately concrete** — what's recorded, what may be published,
  what's their choice, and a written ask before any clip featuring them. Say the same thing
  out loud at the top of the first recording; that verbal moment is the record that matters.
- **The "missing a week costs nothing" line is a retention device.** The most common way a
  free cohort dies is one missed session turning into permanent drop-off. Kill that fear now.
- **The reply ask is the point of the email.** A reply confirms delivery, converts a form
  submission into a commitment, and tells you what to emphasise. Keep it to one question.
