# Session 3 polls — four launches

**Facilitator notes. Not student-facing.** Follow the same operating rules as
[`S2-polls.md`](S2-polls.md): create the polls in the Zoom web portal on the scheduled
meeting, make every poll anonymous, find the launch control before the session, and share
results aloud unless the instructions say otherwise.

Polls A and B turn teaching points into committed choices. Poll C is operationally
load-bearing: it measures which credit-analytics applications are most interesting to this
cohort, and its **top two** results determine the two guided lab demos. Poll D is the same
exit pulse used in earlier sessions.

---

## Poll A — “Can the model approve this?” · launch 0:07

**Why:** participants often treat PD as the final credit decision. This poll makes the policy
layer visible before the adjudication slide and notebook output explain it.

One question, anonymous, 30 seconds.

**An applicant has a low PD in the Approve zone, but DSCR is below the bank’s hard floor.
What is the decision?**

- Approve — the model says risk is low
- Refer — a human should decide
- Decline — the hard policy rule acts first
- It depends on the quoted interest rate

**Share the results.** The intended answer is **Decline** in this workshop’s policy sequence.
Say: *“The model supplied one signal. The policy layer owns the customer outcome.”* Then
advance to the hard-knockout / PD-zone / refer-override sequence.

---

## Poll B — “What makes the watchlist useful?” · launch 0:29

**Why:** AUC is familiar, so participants may reach for it even when the business can review
only 10% of the portfolio. This poll commits them before the operational metric is revealed.

One question, anonymous, 30 seconds.

**A relationship-management team can review only the riskiest 10% of accounts. Which metric
most directly tells you whether that queue contains future deteriorations?**

- Accuracy
- AUC
- PR-AUC
- Top-decile capture
- Training-sample lift

**Share the results.** The intended answer is **top-decile capture**. AUC and PR-AUC remain
useful model diagnostics, but capture at the available review capacity maps directly to the
workflow. Connect it to **21.6% captured = 2.16× lift** on held-out accounts.

---

## Poll C — “Which applications interest you most?” · launch 0:47

**Why:** the full lab contains four useful exercises, but a 90-minute session has room for
only two 15-minute guided demos. This is an interest assessment, not a knowledge question.
The cohort’s interests decide what happens live.

One anonymous **multiple-answer** question. Configure it so participants can **select up to
two** responses. Allow 45 seconds.

**Which applications of credit analytics are you most interested in exploring tonight?
Select up to two.**

- Credit approval / adjudication — combine model PD with policy rules
- Risk-based pricing — connect risk, capital, ROE/RAROC, and rate setting
- Early warning / monitoring — prioritize a deterioration watchlist
- Line management — target safe and profitable line-increase offers

**Share the results and read all four totals aloud.** Rank by votes and use the **top two** as
the guided lab demos from 0:50–1:20, highest first. Paste the winning order in chat.

If second place is tied, run a ten-second chat runoff between only the tied applications. If
the runoff is still tied, default to **Adjudication + Monitoring**. Do not add a third demo;
the remaining exercises stay available in `workshop/labs/S3_4-lab.md` for follow-up.

Use this line to set expectations:

> “You have now selected tonight’s two deep dives. We will still connect all four applications
> in the debrief, but we will not rush four labs into thirty minutes.”

---

## Poll D — “One question before you go” · launch 1:29

Use the same anonymous exit pulse as Sessions 1 and 2. Twenty seconds. **Do not share these
results on screen.**

**Tonight was:**

- Too slow — I wanted more
- About right
- Too fast — I lost the thread
- I got stuck on setup and missed most of it

Read the report after the session beside the S1 and S2 results. In addition to pace, compare
Poll C’s interests with the questions participants asked during the demos; that is useful
input for future cohorts and for how much time each application receives.

---

## Before the day

- [ ] Create all four polls on the scheduled meeting and mark them anonymous.
- [ ] Configure Poll C for multiple answers and verify that participants can select up to two.
- [ ] Put Poll C’s four options in the same order as the four notebook sections.
- [ ] Confirm the co-host can launch Poll C while the facilitator is returning from notebook
      §4 to the lab-handoff slide.
- [ ] Keep a blank chat message ready for the two winners and their demo order.
- [ ] Download the poll report afterwards. Poll C is an interest signal, not an assessment
      score; preserve all four totals.
