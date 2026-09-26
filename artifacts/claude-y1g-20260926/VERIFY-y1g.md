# y1g verify: NO-GO (Answering-from-memory thread, 17:06 UTC 2026-09-26)

DEV diagnosis, plain MiniCPM5-1B, y1f's L1 layout, every earlier user turn (PLAN.md, sealed db138a0ea; rental run
on builder-outbox, RESULTS-gpu.md; ~$0.10).

## Verdict (PLAN.md pick(), applied by script, recounted)
| config | answerable right (of 56) | answerable wrong-candidates | never-told "don't know" (of 10) | eligible |
|---|---|---|---|---|
| A0 plain, unchecked | 26 | 27 | 1 | (control) |
| A1 checked | 26 | 24 | 2 | no |
| C3 3 of 5 tries agree | 16 | 5 | 6 | no |
| C4 4 of 5 tries agree | 10 | 1 | 9 | yes |
| V own yes/no check | 10 | 5 | 9 | yes |
Winner C4; GO needs >= 18 right: **NO-GO**. Per PLAN.md the next change is trained doubt.
Recount: this thread re-derived C3/C4/V from each row's samples, agreement and check answer, re-ran the agreement test
and the 336 scorer on every config of all 71 rows (rows sha256 914c0788...420ce): 0 mismatches, same counts, same pick.

## Proved-wrong test: not triggered
Every config shows the doubt signal (signal(), of the asks A1 answers): C3 keeps 61.5% of A1's right answers and 28.1%
of its wrong ones, C4 38.5% vs 6.2%, V 38.5% vs 18.8%. Shown on DEV: the 1B's own tries carry real information about
when it is wrong. The kept share of right answers is too low to use as is.

## Why right answers were dropped (report only, computed after the verdict from the rows)
- Of the 16 right A1 answers that C4 dropped, 9 had at least 3 of 5 tries that the 336 scorer grades right. The
  hand-written agreement test demanded every content word of the greedy answer ("Twin boys, Sten and Viggo." against
  a try "Sten and Viggo." counts as disagreement). So much of the loss is the scaffolding's word match, not the model.
- The other 7 had 0 to 2 right tries: at T 0.7 the 1B's tries are noisy ("Work, church, blank."), so stability is
  measured under heavy noise.
- V says "no" to most answers: 15 of 26 right, 23 of 28 wrong, 7 of 8 answered never-told. It leans to "no" and
  separates weakly.
- Suggested, untested: a looser match or a lower temperature would keep more right answers. Not done: it would be
  tuning a hand-written rule on DEV after seeing it, and the Redirect asks for the learned version.

## Next (PLAN.md fallback, source switched before sealing)
Trained doubt: the 1B practises answering from chats in the L1 layout; code grades its own drafts; right drafts are
kept as its targets, and questions it gets wrong or was never told get the fixed "I don't know." Per Ben's 16:39 "Use
GLM" (goals page 5f38f110e) the practice chats are GLM 5.3 Flash wording on code-chosen facts, never Claude text or
code templates; an old corrected value is graded wrong (Wrong answers stated as fact, 16:15 UTC). Brain: people learn
when to trust a recollection from being corrected (calibration from feedback), not from a fixed rule.

## Plain summary for Ben
Asking the small model the same question five times and keeping its answer only when four tries agree cut wrong
answers from 24 to 1 and made it say "I don't know" to 9 of 10 things it was never told. But it also threw away too
many right answers (26 down to 10), so it failed the bar of 18 set beforehand. The model does know when it's shaky;
our word-matching check was too strict and the tries too random. Next, the model learns when to say "I don't know"
from practice chats written by GLM, graded by code.
