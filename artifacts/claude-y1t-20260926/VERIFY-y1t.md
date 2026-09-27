# y1t verify: NO-GO (Answering-from-memory thread, 2026-09-27 18:15 UTC)

Trained doubt: a rank-16 LoRA on plain MiniCPM5-1B, trained on its own graded drafts of GLM practice chats (right
answers plus "I don't know."), scored on the sealed DEV bank (PLAN.md, sealed in SEAL-y1t.sha256.txt, sha256
1890893b...). Run: the second vast run, job rent-y1t-vast-p1b, kit 44c385094 (ADDENDUM-11), one RTX 5000 Ada at
$0.35/h, all 6 steps rc=0, $0.20 (builder-outbox 8d2f5e9d5, artifacts/claude-y1t-20260926/run2/RESULTS-vast.md). The
first vast run (run/, PARTIAL, $0.19) stopped at training on a missing nltk and trained nothing.

## Verdict (PLAN.md decision rule, A1 on DEV, counted from the rows files)
| model | answerable right (of 56) | answerable wrong-candidates | never-told "don't know" (of 10) |
|---|---|---|---|
| bar for GO | >= 22 | <= 8 | >= 8 |
| trained (merged) | **22** (met) | **20** (missed) | **5** (missed) |
| plain 1B, same machine | 26 | 24 | 2 |

Two of the three bars are missed: **NO-GO**. Per PLAN.md, bank E stays unused and the next step is decided after
this report. The plain 1B's counts match y1g's own run (26 / 24 / 2).

Rows: eval/y1g_rows.jsonl (sha256 27b68960...) and eval_plain/y1g_rows.jsonl (sha256 0e1efc72...), 71 asks each:
56 answerable, 5 partial, 10 never-told. The counts above were taken from each row's label_A1 and agree with both
y1g_summary.json files. The y1g script's own "pick" line in the logs is y1g's rule, not y1t's, and is not used.

## Proved-wrong test: not triggered
The rule fires if practice-dev never-told "don't know" rises by at least 30 points while DEV never-told "don't know"
rises by fewer than 3 of 10. Practice-dev (bm-398r's dev_check, train398r.json): 100 of 145 before, 136 of 145 after
the LoRA (69.0% to 93.8%, +24.8 points, under 30). DEV: 2 to 5 of 10 (+3, not fewer than 3). Neither half holds.

## Report (fixed in PLAN.md; computed after the verdict)
- Of the plain 1B's 26 right answerable asks, 17 stay right; 5 become wrong and 4 become "don't know". 5 asks become
  newly right (4 were wrong, 1 was "don't know"). Of the plain 1B's 24 wrong answers, 14 stay wrong, 6 become
  "don't know" and 4 become right.
- Never-told: 3 of the plain 1B's 8 wrong answers become "don't know"; the 2 it already declined stay declined.
- By ask type, right (plain to trained) / wrong (plain to trained): one_hop 8 to 6 / 5 to 4; two_hop 5 to 6 / 5 to 2;
  reversal 4 to 5 / 5 to 3; yes/no 3 to 3 / 5 to 5; edit 6 to 2 / 4 to 6; partial (not in the 56) 0 to 0 / 4 to 1.
  Edit asks (a value that was later corrected) lose the most: 4 right answers fewer, 2 wrong more.
- Practice-dev overall: 192 to 235 of 291 right; asks with a value 92 to 99 of 146.
- Drafts (1,762 items): the plain 1B's greedy answer was right on 490 of 888 answerable items and 30 of 53 corrected
  ones; it said "don't know" on 719 of 874 never-told twins. Targets: 490 own greedy answers, 223 own samples, 175
  "don't know" where every try was wrong; "don't know" rows capped at the 713 answer rows; 2,852 rows (each twice).
- Training: 357 steps, loss 0.47 to 0.20 (first and last 10), 6.9 minutes of training in an 8.5-minute step. The adapter (sha256 a4bfaf19...) is on
  the Mac at ~/y1t-adapter and was never pushed.

## Predictions (made before the run)
GO 0.25: no. DEV never-told "don't know" >= 8: 0.6: no (5). DEV right >= 22: 0.4: yes (exactly 22). Proved
wrong 0.2: no.

## What this shows (labelled)
- Shown: training on its own graded drafts of GLM chats made the 1B decline much more on held-out GLM chats (+24.8
  points) and a little on DEV (+3 of 10). On DEV it gave 4 fewer wrong answers and 4 fewer right ones.
- Suggested, not tested: the plain 1B already declines 69% of the time on the practice chats but 2 of 10 on DEV, so
  what it learned is mostly tied to the GLM chats' form. Edit asks got worse, which fits training data with few
  corrected values (53 of 1,762 items).
- The H1 rows (artifacts/claude-y1tH1-20260926/run) belong to the Wrong-as-fact thread and were not opened here.

## Recount
A separate checker (a read-only worker that did not see these counts) recounted label_A1 in both rows files, matched
asks by (life_id, turn_index), and read train398r.json. It got the same numbers: trained 22 / 20 / 5, plain 26 / 24 / 2,
17 of the plain 1B's 26 right asks still right, practice-dev 100 to 136 of 145 (+24.83 points), and no mismatch
with either summary file. It reached the same result: NO-GO, and the proved-wrong test does not fire.
