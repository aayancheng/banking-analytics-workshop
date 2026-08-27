# Confirmation email — pilot cohort

**Facilitator notes. Not student-facing.** Template only: no names, no live links — keep it
that way, this repo is public. The attendee list stays out of git.

**Send:** individually, not BCC. Fourteen sends is about half an hour, and this is the one
email whose entire purpose is to earn a reply. Use a group list for later logistics, not this.

**Cohort as of Aug 26 — 14 distinct sign-ups** (after removing 2 own test rows and 1 duplicate):
9 "yes live" · 4 "recording only" · 1 "recording then join later" → **expect ~9 live, realistically
6–8 on the night.** Regions: 8 Toronto/NA · 3 HK/Asia · 3 "Elsewhere". Background: 11 of 14 are
credit risk, which is exactly the target audience.

**A third of the cohort signed up for the recording, not the room.** Don't optimise this email
purely for live attendance — the async paragraph is load-bearing for five people.

**The Tally consent checkbox covers the *free pilot / candid feedback* terms — NOT recording
consent.** That still has to be stated in this email and out loud on the night.

**Fill in before sending:** `{{FIRST_NAME}}`, `[[MEETING_LINK]]`.
**Attach:** `credit-analytics-workshop.ics` — regenerate it with
`python workshop/facilitator/make_ics.py 1` (Session 1 only, since S2–S5 aren't locked).

**Hong Kong recipients:** change the subject to *"…starts Friday Sep 11, 8:00am HK"*. Their
calendar day differs from the one in the body, and the subject is what people skim. The
`.ics` carries a 12-hour alarm, which lands the evening before for HK.

**If you end up on a time-capped free tier**, add the optional two-link block marked below.
Don't add it otherwise — it's friction nobody needs to read about.

**Then diarise:** a short reminder on the morning of *their* Sep 11.

---

## Subject

> You're in — Credit Analytics with AI Agents starts Thursday Sep 10

*(HK variant: "You're in — Credit Analytics with AI Agents starts Friday Sep 11, 8:00am HK")*

---

## Body

Hi {{FIRST_NAME}},

You're confirmed for the pilot cohort of **Credit Analytics with AI Agents** — five sessions,
90 minutes each, free.

**Session 1 is locked in:**

| | |
|---|---|
| **Toronto** | Thursday **Sep 10**, 8:00–9:30pm EDT |
| **Hong Kong** | Friday **Sep 11**, 8:00–9:30am HKT — note it's the *next* calendar day |

Calendar file attached. It'll land in your own time zone, so you don't have to do the maths.

Sessions 2–5 run weekly, same time. I'm holding off on locking those dates until I've heard
from the group — if Thursday evening doesn't work for you across five weeks, say so in your
reply and I'll factor it in. Better to sort that now than to lose people in week three.

**Join:** [[MEETING_LINK]]

<!-- OPTIONAL — only if the platform has a time cap:
We take a five-minute break about 45 minutes in, and the second half uses a different
link: [[MEETING_LINK_2]]. Both are in the calendar invite too.
-->

---

### One thing to do before Sep 10 — about 10 minutes

Please get a green check *before* the session:

1. Go to **github.com/aayancheng/banking-analytics-workshop**
2. Click **Code → Codespaces → Create codespace on main**
3. Wait for it to build, then run: `python verify.py`
4. You're looking for: **✅ Stage 0 verified — you are here, and it works.**

That's the entire setup. Nothing installs on your laptop, and it runs the same whether you're
on a Mac, a PC, or a locked-down work machine.

If it doesn't go green, reply and send me what you see. I'd much rather fix it this week than
spend our 90 minutes on it.

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
- **If you signed up for the recordings rather than the live sessions, that works** — the
  material is built for it. Recordings go out within a couple of days, every checkpoint is
  self-sufficient, and you'll end up in exactly the same place, just on your own clock.
- Bring questions. It's a small group, small enough that this can be a conversation, and I'd
  rather it were one.

### One reply, two lines

Hit reply and tell me:

1. **What's the one thing you want to be able to do at the end of five weeks?**
2. **Does Thursday 8:00pm EDT work for you for the rest of the series?** — or if you're in
   Hong Kong, Friday 8:00am.

This is a pilot with fourteen people in it, so yours is genuinely one voice in fourteen.
I'll shape the sessions, and the schedule, around what comes back.

See you on the 10th.

Yan

---

## Why it's built this way

- **The pre-work ask is the real payload.** At 90 minutes there is no room for a setup sweep,
  and `stage-0` exists precisely so it can happen beforehand. It's a 10-minute task with a
  specific success string to look for, not "please get set up".
- **Only Session 1 is committed.** Announcing five dates and then moving them costs more trust
  than announcing one and confirming the rest. The uncertainty is turned into an ask, which
  is both honest and useful — you need the scheduling data anyway.
- **The consent language is deliberately concrete** — what's recorded, what may be published,
  what's their choice, and a written ask before any clip featuring them. Say the same thing
  out loud at the top of the first recording; that verbal moment is the record that matters.
  With ten identifiable practitioners rather than four, this matters more, not less.
- **"Missing a week costs nothing" is a retention device.** The most common way a free cohort
  dies is one missed session becoming permanent drop-off. Kill that fear before it forms —
  and it's especially load-bearing while the later dates are still moving.
- **The reply is the point of the email.** It confirms delivery, converts a form submission
  into a commitment, and tells you what to emphasise. Two short questions is the ceiling;
  a third would cost you replies.
