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

## Labeller fix, k1e-teacher-c (added 2026-09-26 18:50 UTC): FAIL, the critic waits
Sealed before any call (SEAL-teacher-c.sha256.txt, b7573e0ae); Mac job k1e-teacher-c, rc 0, 41 OpenRouter calls,
about $0.03. Recomputed here from the pushed labels with the same agree code: the same numbers.

| Labeller (one change from phase 1) | Half | Agree | Kappa | GLM useful | Judges useful |
|---|---|---|---|---|---|
| reasoning "high" | A (78) | 61 | 0.56 | 38 | 25 |
| majority of 3, temperature 0.7 | A (78) | 60 | 0.53 | 37 | 25 |
| reasoning "high" (chosen on A) | B (79), the check | 63 (80%) | 0.603 | 43 | 31 |

The check needed 68 of 79 (85%): **FAIL**. Both changes stay lenient (GLM "useful" about 1.4 times as often as the
judges). As agreed with the Thread manager before the run: no third labeller is tried without telling them, and the
critic is not trained on GLM labels.
