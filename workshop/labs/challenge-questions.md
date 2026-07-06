# The Challenge-Question Bank (S5 defense round)

Twenty questions a validator would actually ask. Panelists: pick 4–6, at least one from each block. Defenders: yes, you may read this in advance — real validators publish their expectations too. Knowing the question is not the same as surviving the follow-up.

## Data & leakage
1. Your data is synthetic. Name two conclusions from tonight that would NOT transfer to real data, and one that would.
2. Walk me through what stops `pd_default_origination` from entering a model. Not the intention — the mechanism.
3. If I regenerated the data with seed 43, which of your headline numbers would move, and roughly how much?
4. Your default rate is 16.7%. Your bank's SME book runs at 2–4%. Does that gap matter for anything you built?

## The scorecard
5. Defend using logistic regression in the age of gradient boosting — to a CTO, not a regulator.
6. Your top variable: why is it in the model, and what evidence would make you remove it?
7. Your band table: what exactly does monotonicity prove, and what does it NOT prove?
8. A declined applicant demands the reason. Produce it from your artifacts, right now.

## Decisions & pricing
9. You chose a cutoff. Who loses under your cutoff that would win under the challenger's ranking — and why are you comfortable with that?
10. Policy knockouts made most of your declines before the model voted. Why have a model at all?
11. The pricing engine says your AAA band is the most mispriced. Convince me that's not a bug.
12. Your engine has no ML. What could still go wrong with it in production, and how would you know?

## Monitoring & the honest gate
13. Your EWS AUC is 0.662. My policy says models below 0.70 don't ship. Respond.
14. Why is capture-at-decile the right gate for a watchlist, in one relationship manager's workday?
15. When is it legitimate to change the data instead of the gate? What proof must accompany it?
16. Your line-increase model offers to 95 of 8,336 accounts. Your CRO asks why so timid. Defend it — then tell me what you'd change if growth were the mandate.

## The human-agent team
17. What did the agent build, and what did YOU verify? Name one thing you checked and one thing you chose to trust.
18. Your agent's training run passed a gate you never read. Is that your pass or its pass?
19. If an agent proved your favorite gate was unreachable, what are your two legitimate moves — and who decides?
20. You have ten minutes of tokens left and an unreviewed model. What do you spend them on?
