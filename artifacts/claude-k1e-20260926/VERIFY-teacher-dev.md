# k1e teacher, phase 1: GLM labels vs the blind judges on DEV (Creative answers in chat thread, written 2026-09-26 17:58 UTC)

**FAIL on the label rule fixed before the run (>= 85% agreement AND kappa >= 0.5): 121 of 157 (77%), kappa 0.537.**
So the critic is not trained on these labels. Checked by the thread from the pushed labels with the same script
(scripts/claude_k1e_teacher.py agree): the same numbers.

Run: Mac job k1e-teacher-b (runs/k1e-teacher-b on builder-outbox, rc 0; OpenRouter, GLM 5.3 Flash, reasoning low,
32 calls, about $0.02; the key stayed with the script). Files copied here from builder-outbox:
teacher-dev/labels.jsonl (157), train/items.jsonl (240 GLM-written practice chats, all slots filled), teacher-log.txt.

| | GLM useful | GLM not useful |
|---|---|---|
| judges useful (56) | 48 | 8 |
| judges not useful (101) | 28 | 73 |

GLM calls a draft useful far more often than the blind judges do (76 vs 56): 28 of the 36 disagreements are GLM
"yes" where the judges said "no". Made-up counts were not part of the rule.

What this means (inferred): as used here, GLM 5.3 Flash is a lenient labeller. A critic trained on its labels would
learn GLM's looser idea of useful, not the judges'. The 240 practice chats are unaffected (they are GLM-written, the
labels are the problem).

Next (a plan, not sealed): one change to the labeller, chosen on one half of DEV (split by chat) and checked once on
the other half against the same rule before any training: either GLM with reasoning effort "high" instead of "low",
or the majority of 3 GLM labels per draft. Cost about $0.05 on OpenRouter, Mac CPU only.
