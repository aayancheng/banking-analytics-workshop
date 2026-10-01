# T−1 reminder — send Sep 30

**Facilitator notes. Not student-facing.** Template only: no names, no live list.

**Send to the join-link audience**, not everyone:
`python workshop/facilitator/cohort.py --live --unknown`
The recording track gets the video afterwards and does not need a join link. **Re-export
from Tally on the morning of Sep 30** and regenerate — the script prints the newest sign-up it
contains, so a stale export says so. Everyone in **Bcc**, you in To. **Use Gmail's Schedule
send.** Over ~90 addresses, split into two sends.

**Hong Kong:** their session is *Friday Oct 2, 8:00am HKT*. Send the short personal note on the
morning of *their* Friday as well — a Wednesday-evening Toronto reminder lands while they sleep.

**What state are they in?** On `main`, seeing "Stage 5 verified", as after S2 and S3. This email
does not ask for any stage jump. The one new pre-work step is `git stash -u && git checkout main && git pull` (S3's robust sync: it also rescues anyone who stayed on a stage tag, where a bare `git pull` fails) **then** the container rebuild
(the rebuild reads the pulled `devcontainer.json`, which is what adds Quarto), then `verify.py`. It is deliberately optional in effect: the lab's checks are plain Python, so a failed
rebuild costs the rendered preview and nothing else. Say so in the email so nobody arrives
anxious about it.

---

## Subject

> Tomorrow, 8pm EDT — Session 4, the finale: model documentation a validator accepts (Friday 8am in Hong Kong)

## Body

Hi everyone,

Session 4, the finale, is tomorrow. Everything you need is in this email.

**JOIN**
`[[MEETING_LINK]]` — same link as before.

**WHEN**
Toronto: Thursday 1 October, 8:00–9:30pm EDT
Hong Kong: Friday 2 October, 8:00–9:30am HKT — the next calendar day

**WHAT WE BUILD**
Model documentation a validator accepts. The platform's documentation becomes a wiki — a site,
a validation PDF and an e-book, all from one source — where every number is generated from the
repo, and `python verify.py` fails on a stale or hand-typed number. We walk through the Business
Credit Score chapter and its open findings. Then, in pairs, you draft one part of the
adjudication model's chapter with an AI agent and self-check it.

**BEFORE YOU JOIN — ABOUT 10 MINUTES, TODAY**

1. Open your Codespace (github.com/aayancheng/banking-analytics-workshop → Code → Codespaces).
   In the terminal, run:

   ```
   git stash -u && git checkout main && git pull
   ```

   This puts you on `main`, wherever the last session left you (nothing is lost: any local
   changes are stashed), and brings in the change that adds Quarto, the tool that renders the wiki.
2. Then open the Command Palette and run **Codespaces: Rebuild Container**. It takes about
   5 minutes. The order matters: the rebuild reads the configuration you just pulled.
3. When it finishes, in the terminal:

   ```
   python verify.py
   ```

   You want the green line ending: **you are here, and it works.** "Stage 5 verified" is the
   right answer.
4. If the rebuild fails, or you run out of time, come anyway. The lab's checks are plain Python
   and work without it; only the rendered preview needs Quarto.
5. If `verify.py` is red, reply today and I'll sort it with you before we start.

**AI AGENT FOR THE LAB**
GitHub Copilot is free in Codespaces, and Claude Code works too if you have it. Either is fine.

**MISSED AN EARLIER SESSION, OR WANT TO REWATCH?** The Session 1–3 chapter videos
are on the YouTube channel TeamYan (@teamyan2026): https://www.youtube.com/@teamyan2026

Same two rules as last time: questions in the **chat**, not on mic; and the session is
**recorded**, so if something breaks on your end, nothing is lost.

See you tomorrow.

Yan

---

## Why it's shaped like this

Same single job as the S1 and S2 reminders — get people into the room with a working
environment — plus one new pre-work step that must not become a reason to stay away.

- **The link is first**, before any prose. On the night, people scroll to the top and click.
- **The order is pull, rebuild, verify.** The rebuild uses the `devcontainer.json` in the
  workspace, so Quarto only arrives once the pull has run. The cost (about 5 minutes) is named
  so it can be scheduled rather than discovered at 8:01.
- **The fallback is stated plainly.** "Come anyway" removes the failure mode where someone
  whose rebuild broke decides not to join. The lab is designed so Quarto is a preview
  convenience, not a dependency.
- **"Stage 5 verified is the right answer" is repeated**, as in S2, to prevent a round of
  "is mine wrong?" in the chat.
- **Agents are named once** so nobody wonders whether they need a paid tool.
- **The recording line is one line.** Nothing new is promised beyond what the session covers.
