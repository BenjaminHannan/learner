# feas-24: a cheap "still solvable?" head on the frozen 1B (registered 2026-09-25 ~20:25 UTC, before the run)

Source: experiment 3 of the GPT-6 Pro review Ben relayed at 19:13 UTC. Pass marks are the reviewer's, unchanged.
Why: judging whether a partial state can still reach the goal is what worked in Tree of Thoughts (24 game) and is
the kind of warmth Ben wants (not "22 is close to 24"). Before putting any judge into search, test whether a cheap
one ranks live states above dead ends at all. Offline only: no generator, search or LoRA change.

Procedure: scripts/claude_feas24.py (docstring). A partial state is what is left of a 4-card hand (1-13, target 24)
after one step (3 values) or two steps (2 values); its label (can it still make 24) is proved by exact search. The
feature is the frozen 1B's hidden state at the last prompt token; the head is the logistic regression already used
for the idea judge (claude_cre333e_train.fit_lr). Layer (8/12/16/20/24) and l2 (1/30/300) are picked by dev AUC of
the seed-0 real-label head, then frozen. Placebo: the same head trained on labels shuffled within each stage.
Seeds 0, 1, 2 (each trains on a different 85% of the training pool). One CPU run in this container.

Deviations from the reviewer's design, forced by the data (found by the selftest, before any model output):
- Only 195 distinct 2-value states can make 24, so states are split BY STATE (no state is in two splits), not only
  by hand. Test pairs still come only from held-out test hands (a quarter of the 1,820).
- Training is 1,878 balanced states per seed (not 2,000) and dev is 342 (not 400).
- Test reachable states repeat across pairs (the selftest counts about 72 distinct in the 3-value pairs and about 26
  in the 2-value pairs); every pair is distinct and no dead-end state is reused within a stage. Reported.

Marks (200 matched pairs: 100 with 3 values, 100 with 2; a pair is right when the head scores the reachable state
higher; ties count half):
- PASS = in EVERY seed: real-label head right on at least 150/200 pairs, AND at least 30 more than the shuffled-label
  head of the same seed, AND at least 70/100 of the 3-value pairs.
- Proved wrong (for this cheap head): real-label head right on 110/200 or fewer in all three seeds AND no more than
  10 above its shuffled-label head.
- Otherwise: NOT SHOWN (reported with counts).
Interpretation limit (reviewer): a pass shows useful ranking on this panel, not a faster search. Only then would a
separate test use the head as a soft priority in search, never as a hard prune.
