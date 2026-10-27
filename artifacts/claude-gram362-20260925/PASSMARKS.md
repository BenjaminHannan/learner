# gram-362 pass marks (grammar thread, registered 2026-09-25 before any run on chatpanel362)

## Question
338 already samples 4 drafts per chat reply and keeps the first one that passes its guards. About 3 in 4 drafts
are clean. Can a small learned "inner critic" on the 1B itself put the clean drafts first, so more replies are
clean, without making them less helpful?

## The one change
Before 338's guards see the 4 drafts, CriticGen362 orders them by a critic score, best first. 338 then keeps the
first draft that passes its guards exactly as today. Nothing else changes: temperature 0.7, top_p 0.9, 4 samples,
guards G1-G4, 338b, 12-message history. Code: scripts/claude_gram362.py (Critic362, CriticGen362,
run_chat_component). Head: artifacts/claude-gram362-20260925/critic_head.json (features ["stats"]).

The critic: logistic regression on 12 signals from one extra pass of the same loaded 1B over each draft in its chat
context (critic_stats, STATS362): how unlikely the 1B found the draft's words (mean, lowest, 3rd lowest, worst
5-token stretch, share and counts of unlikely tokens), length, a reply cut off after a list number, no end mark,
repeated word triples, repeated sentences. No new model and no new download.

## Training (training prompts only, never a test panel)
320 training prompts written for this step (names A-J, kinds smalltalk/feelings/advice/explain/creative), 4 drafts
each from the 1B at 338's settings = 1,280 drafts. Each draft graded by two blind Opus graders with the neutral
grammar question (8 grader runs, each file with 10 planted errors and 10 planted clean lines: caught 10,9,10,10 and
10,9,10,10; clean kept 10/10 in all 8). Graders agree on 1,201 of 1,280. Label = clean by both: 945 of 1,280.
Scripts: scripts/claude_gram362_train.py stats / train.

Cross-validated on the training prompts (5 folds by prompt, report only):
| picker | prompts whose kept draft is clean (of 320) |
|---|---|
| first draft (today) | 241 |
| critic (stats, L2 0.01), AUC 0.706 | 266 |
| hidden-state critic (tried, not used), AUC 0.672 | 255 |
| perfect picker | 311 |

So the expected gain is about +5 to +8 points, not a jump to 99%. This step is one piece toward the 99% goal.

## Test
chatpanel362 (artifacts/claude-chatpanel362-20260925, sealed, unread): 12 conversations, 112 user messages
(smalltalk 27, advice 24, followup 21, feelings 20, explain 20), names P-T. Component test on CPU exactly as
gram-361: 338b's chat layer on a stub agent that always gives up, so the 1B answers every turn under the real
guards and history. Arms base (today) and critic (the change), same seeds per turn (3620 + 100 x conversation +
turn), so each turn's first 4 drafts are the same until the conversations' histories differ.
  python -B scripts/claude_gram362.py --panel <panel>/turns.jsonl --gen-model <MiniCPM5-1B 87179e5c> \
      [--critic] --out <run>/arm_{base,critic}.jsonl --tmp <scratch>

## Grading and judging
scripts/claude_gram362_score.py prep: two blind Opus graders, each one shuffled file with both arms' distinct
replies + 336's 40 planted errors + 40 planted clean lines (seeds 3631, 3632); the same neutral question as
gram-361. A grader is valid only with >= 36/40 planted errors caught and >= 36/40 clean kept. One blind Opus
helpfulness judge sees each turn's earlier user messages, the user message and the two replies in random order
(seed 3633) and picks the more natural and helpful reply for a friendly chat assistant, or "tie".

## Marks (fixed now)
| Mark | What | Bar |
|---|---|---|
| P362.1 | critic replies graded clean, each grader | >= 90% |
| P362.2 | gain over base (critic % minus base %), each grader | >= +5 points |
| P362.3 | helpfulness: critic preferred or tied | >= 50% of turns |
| P362.4 | turns where every sample failed the guards (the give-up line stays) | critic <= base + 3 |
| P362.5 | most common critic reply, not counting 338b's fixed "I'm not sure" line or the give-up line | <= 5% of turns |

Proved wrong: if either valid grader gives the critic less than base + 2 points, the 1B's own word probabilities
cannot tell its clean drafts from its broken ones well enough to help.
Report only: reply length per arm (the critic leans to shorter drafts: length alone has AUC 0.37 against clean);
per-kind clean counts; guard counts from the stats line; CPU time per turn.
