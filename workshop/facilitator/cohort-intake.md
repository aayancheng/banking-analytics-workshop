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

Export from Tally, then:

```bash
python workshop/facilitator/cohort.py --since 2026-08-31
```

Prints the stats and a comma-separated **Bcc list of only the people who signed up after that
date** — deduplicated on email, with your own test rows dropped. Paste into Gmail, reuse the
body of the last send, done.

Run it with no `--since` for the whole cohort, `--live` for only those attending live. The
export is PII and gitignored; the script is not.

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

## What changes now the cohort is ~46, not ~16

Sign-ups roughly tripled, and some of the material still assumes a small room. Free-event
attendance typically runs 40–60% of those who said yes, so **expect 15–25 live**, not 46.

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
