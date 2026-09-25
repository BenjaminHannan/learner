# lis-318: the lis-301 reader, retrained with chatty conversation rows (one change)

Thread "Fix: reading facts from chat" (cmsg_01FuvegZXjMmeUzStiEFVnEWFFJdDCbBKsf18JUgMQeEYH). Written 2026-09-25 ~02:30 UTC,
before any chat row was relabelled, any training ran or the panel was run. Ben's ask (00:31 UTC): fix reading facts
from chat (336: saved 57%, answerable asks right 22%).

## Diagnosis this follows (lis-317, DEV only, RESULTS.md)
The lis-301 reader finds 89/131 DEV chat facts before any gate and invents some on chatty turns (smalltalk read as a
fact, corrections saved with the old value). A sampling-agreement gate fails its pre-fixed selection rule. lis-301's
training rows are mostly short tidy sentences; its "proved wrong" clause was about the confidence gate on tidy text,
not about reading chat.

## The one change
Training data. lis-301's data is rebuilt unchanged (scripts/claude_lis301_data.py), then about 2,500 new chatty rows
written from scratch by 5 Opus agents (brief: data/WRITER.md; dialogs of 4-8 turns; families teach_multi, teach_passing,
pets, correct, ask, smalltalk-with-names, nosave, short_answer, pronoun) are added. Only rows a blind second Opus
labeller reproduces (scripts/claude_lis300_agree.py) are kept. 10% of dialogs go to dev (src chat318_dev), the rest are
repeated 4 times in train. Builder: scripts/claude_lis318_data.py.
No LoCoMo or LongMemEval text, and nothing built from them (the Benchmarks thread's test and final exam). The writers
never saw readpanel318, bank A/B or any panel; they avoided every DEV name.
Unchanged from lis-301: base model and snapshot, LoRA settings, epochs 2, lr 2e-4, rank 32, batch 16, max-len 256,
seed 300, prompt (turn + previous reply only), frame format, confidence, compiler, the threshold rule (smallest grid T
with 0 dev wrong-save turns under the lis-300 scorer, else 0.995).

## Registered test
artifacts/claude-readpanel318-20260925 (TEST-ONLY, sealed 00:50 UTC 09-25, 240 chatty turns, 255 facts, written blind by
a separate Opus agent; a blind second labeller agreed 255/255). Run ONCE per arm, counts only.
Arm A = lis-301 reader at T 0.995 (live). Arm B = lis-318 reader at its dev T.
Scorer: scripts/claude_lis318_score.py (per-fact release; owner + value matching; relation not graded since the panel
uses free relation words).

## Marks (fixed now)
| Mark | Bar |
|---|---|
| Q1 reads chat: B's R0 (gold facts in the greedy read, saving mode, no gate) | >= 217/255 (85%) AND >= A's R0 + 38 (15 points) |
| Q2 saves more: B's saved_right at its T | >= A's saved_right + 40 |
| Q3 safe: B's wrong_turns at its T | <= 2 of 240 |
| Q4 no invention: B's nofact_rows_with_save (75 nosave + smalltalk rows) | <= 1 |
| G1 no forgetting: lis-301's original dev (all-or-nothing hits, lis-300 scorer, each arm at its T) | B >= A - 23 (3% of 761) |
| G2 speed: B median read ms on the rental GPU | <= A median + 200 |
PASS = all six. Proved wrong: B's R0 <= A's R0 + 13 (5 points) -> chat rows are not the lever; the next step is a
different mechanism (more context, open relations, or a learned checker), not more rows.

## Report only
Per-kind counts, held_right (what confirm-at-use could still recover), T and the dev sweep, B's dev numbers per src,
B on the lis-317 DEV rows (R0, saved at T), training minutes, dollars.
