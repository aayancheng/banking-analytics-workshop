# Cohort intake — confirming sign-ups without doing it by hand

**Facilitator notes. Not student-facing.**

Sign-ups arrive continuously; batch emails go out occasionally. The gap between those two
facts is where people sit unconfirmed and quietly go cold. Two layers close it.

## Layer 1 — instant, automatic, free: the Tally thank-you page

**Tally's respondent confirmation emails are a Pro feature**, not available on the free plan.
Don't pay for it — the free thank-you page is *better* for this job anyway: it appears
instantly, it cannot land in spam, and it needs no maintenance.

Set the form's thank-you page (Tally → form → *Thank you page*) to say, in this order:

1. **"You're booked."** Say the words. That is the entire question they have.
2. **Both dates**: Thursday 10 September, 8:00–9:30pm EDT · Friday 11 September,
   8:00–9:30am HKT — *the next calendar day if you're in Asia*.
3. **The 10-minute pre-work**, with the repo link and the exact string to look for
   (`Stage 5 verified`). They can act immediately, while motivation is highest.
4. **"Your join link comes by email the day before."** Sets the expectation so nobody
   emails you asking where it is.

**Do not put the Zoom link on that page.** Anyone who submits the form sees it, so the link
would spread past the cohort — and with Zoom Pro capping at 100 participants, an uncontrolled
link is a real capacity risk, not just a tidiness one. Keeping it in email also gives the
reminder a reason to be opened.

## Layer 2 — batch, manual, ~5 minutes: the catch-up send

Export from Tally, then — **keeping the export you last mailed from** — run:

```bash
python workshop/facilitator/cohort.py --not-in <the export you last mailed from>.csv
```

That is an exact set difference: everyone in the new export whose address is absent from the
old one. **Prefer it over `--since`**, which is date-only and cannot distinguish two sends on
the same day. Paste the Bcc list into Gmail, reuse the body of the last send, done.

No filter gives the whole cohort; `--since YYYY-MM-DD` (inclusive) works when you have no
previous export; `--live` narrows to those attending live. The export is PII and gitignored;
the script is not.

The script picks the export with the **newest sign-up inside it**, not the newest file on disk,
and prints that timestamp every run — so a stale export announces itself instead of quietly
producing an old list. Paths resolve against the repo root, so it behaves the same from any
directory.

**Always Bcc, never To.** Over ~90 recipients, split into two sends — Gmail throttles large
Bcc lists and a personal account is likelier to be spam-filtered.

**Do this the day after any burst of sign-ups**, not weekly. A confirmation that arrives four
days late has already done its damage.

## The T–1 reminder

**Sep 9**, to everyone. Write it, then use Gmail's **Schedule send** (the arrow beside Send)
rather than trusting yourself to remember on the day.

Keep it short — they've had the long one:

- The Zoom link, at the top, unmissable
- Both times again, dual timezone, "tomorrow" for Toronto and "Friday morning" for HK
- One line of pre-work: *if you haven't opened the Codespace yet, do it now, it takes 10 minutes*
- Nothing else. No teaching, no new links.

Regenerate the Bcc list the same morning — anyone who signs up on Sep 9 still deserves it.

## Closing sign-ups — close the *live* seats, not the form

**Zoom Pro caps a meeting at 100 participants.** At ~90 sign-ups that is no longer academic:
the export's own split runs about 64% "yes live", so 90 sign-ups implies ~58 intending to
attend, and a strong show rate would put the room near the cap with no headroom for a
re-join after a dropped connection.

**But there is no capacity limit on the recording.** So don't close the form — close the live
seats and keep taking people on the recording track. Nobody is turned away, the list keeps
growing, and the room stays a size one person can actually run.

Edit the Tally form (or its thank-you page) to say roughly this:

> **Live seats for the September pilot are full.**
>
> Around 90 people signed up in three weeks. That is more than I can support live in a
> 90-minute session whose whole promise is that nobody gets left stuck — so I'm capping the
> room to keep that promise.
>
> **You can still join on the recording track.** Every session is recorded and sent out
> afterwards, the repo is public, and every checkpoint is self-sufficient — you will end up in
> exactly the same place, on your own clock. Sign up below and I'll send you the recordings and
> the material.
>
> **Or take a live seat in the next cohort.** Same five sessions, running again after this
> pilot. Tick the box below and you'll get first refusal.

Three things that copy does deliberately: it gives the real reason rather than manufacturing
scarcity, it makes the recording track a genuine option rather than a consolation prize (which
it is — a third of the existing cohort chose it on purpose), and it converts overflow into the
waitlist for cohort two instead of losing it.

**Announce it publicly too.** "Live seats closed, 90 sign-ups in three weeks" is honest social
proof, and it is the single best moment to open the cohort-two waitlist while attention is high.

## Contingency — assume something breaks

At ~40 live, a hiccup stops being a hiccup. Decide these now, not at 8:05.

**Get a co-host.** The biggest single risk reduction available, and it costs one ask. Someone to
watch chat and admit late joiners while you teach. You have two academics in the cohort who
would likely say yes. Solo, you will either teach badly or miss chat entirely.

**Say the backstop out loud in the first minute.** *"Everything tonight is recorded and goes out
tomorrow. If my connection dies, give me five minutes and rejoin on the same link. If yours
dies, the recording has you covered — nothing here is lost."* It costs fifteen seconds, and it
converts a potential crisis into an inconvenience for everybody, including you.

**Zoom settings for a room this size:**
- **Mute on entry** — non-negotiable at 40+
- **Waiting room ON only if you have a co-host.** Solo it is a second job; without one, leave it
  off and **lock the meeting at 8:15** instead, which stops both stragglers and strangers.
- Chat on, but say at the top that questions go to chat, not open mic
- Screen share: host only

**Rehearse the fallback path.** The demo frames (`workshop/demo/frames/frame_01.png`,
`frame_06.png`) are already in the pre-flight. Know which tab they are in without looking.

**The pre-work is your real turnout control.** People who arrive un-green are the ones who
consume the room. The rule — *red at the start means join from Codespaces, we do not debug your
laptop live* — has to be said in the reminder email and again at 0:03. At 40 people it is the
only thing standing between you and a session spent on someone's corporate proxy.

## What changes now the cohort is ~90, not ~16

Sign-ups have gone up more than fivefold, and some of the material still assumes a small room.
About 64% choose "yes live", and free-event attendance runs 40–60% of those, so **expect roughly
35–45 live** out of 90 — comfortably under the 100 cap, but with little headroom if it grows.

Three things to revisit before Sep 10:

1. **"Nobody leaves un-green" is no longer verifiable by sweep.** You cannot check 20+ people
   individually inside 90 minutes. Convert it to a self-report: *"type your stage number in
   the chat"* at the 1:25 checkpoint. It scales, and it still surfaces whoever is stuck.
2. **Questions move to chat, not open mic.** Say so at the top. Twenty people unmuting is a
   different event from six. Consider asking one attendee to watch chat for you.
3. **The room-sweep timing in the containers block was written for a small room.** Rehearse it
   assuming you cannot help stragglers individually — the rule *"red at the start = join from
   Codespaces, we do not debug your laptop live"* is now doing much heavier lifting.

**Zoom:** waiting room on, participants muted on entry. The 100-participant cap on Pro is not
a constraint at this size, but the free tier's 40-minute cap absolutely is — the Sep 9 upgrade
is no longer optional.
