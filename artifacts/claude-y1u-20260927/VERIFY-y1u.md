# y1u verify: NO-GO; the proved-wrong test does not fire (Answering-from-memory thread, 2026-09-27 19:09 UTC)

Plain LFM2.5-1.2B-Instruct (commit 0f604ada), no training, on y1t's DEV check (PLAN.md, sealed in SEAL.sha256.txt at
main a3caafba6; seal 8 of 8 OK at the run). The machine was this thread's cloud container: CPU only, 4 cores, float32,
torch 2.14.0+cpu, transformers 5.17.0, $0. LFM ran 18:20 to 18:47 UTC, 22.1 s per ask. Plain MiniCPM5-1B then ran the
same command on the same CPU, 18:47 to 19:08, 17.3 s per ask. Both ended rc=0 (run/RUN-NOTE.md).

## Verdict (A1 on DEV; y1t's bars; counted from the rows files)
| model | answerable right (of 56) | answerable wrong-candidates | never-told "don't know" (of 10) |
|---|---|---|---|
| bar for GO | >= 22 | <= 8 | >= 8 |
| plain LFM2.5-1.2B | **35** (met) | **18** (missed) | **1** (missed) |
| plain MiniCPM5-1B, same CPU | 26 | 24 | 2 |

**NO-GO.** Proved-wrong test: LFM minus MiniCPM on the same CPU is +9 right and 6 fewer wrong. The test fires only if
both gaps are 2 or less, so it does not fire: LFM's c1-dev lead does carry over to answering from memory on this bank.
Per PLAN.md, the candidate next test is y1t's recipe (trained doubt from its own graded drafts) on LFM, under its own
sealed plan.

Rows: run/lfm/y1g_rows.jsonl (sha256 b3e410cc...) and run/minicpm/y1g_rows.jsonl (sha256 f3e556fe...), 71 asks each,
matched by (life_id, turn_index). Recounted by this thread from each row's label_A1; the counts agree with both
y1g_summary.json files. No separate checker was used this time (the counts are small and the summaries agree).
MiniCPM on this CPU in float32 gave exactly its GPU bfloat16 counts from y1g and y1t (26 / 24 / 2).

## Report (after the verdict)
- Overlap: LFM also gets 21 of MiniCPM's 26 right answers, and 14 that MiniCPM missed.
- By ask type, right / wrong (LFM, MiniCPM): one_hop 13 / 3, 8 / 5; two_hop 6 / 4, 4 / 6; reversal 6 / 3, 5 / 4;
  yes/no 3 / 6, 3 / 5; edit 7 / 2, 6 / 4; partial (not in the 56) 0 / 5, 0 / 4. One-hop asks carry most of the gain.
- Never-told: LFM answered 9 of the 10 with a made-up value; it declines less than MiniCPM (1 against 2).
- LFM's other configs (report only, the y1g script's filters on top of A1): C3 32 / 9 / 4, C4 25 / 7 / 6, V 23 / 11 / 8.
  C4 (keep an answer only if 4 of 5 tries agree) meets the right and wrong bars and misses "don't know" by 2. It is not
  a y1u config, and this is not a verdict on it.
- No greedy reply came near the 200-token cap (longest: LFM 14 tokens, MiniCPM 21).

## Predictions (made before the run)
GO 0.1: no. Right >= 22: 0.65: yes (35). Wrong <= 8: 0.1: no (18). Never-told "don't know" >= 8: 0.25: no (1).
Proved wrong 0.35: no.

## What this shows (labelled)
- Shown: on this bank plain LFM answers more memory questions right than plain MiniCPM (35 against 26 of 56) and fewer
  wrong (18 against 24), on the same machine.
- Shown: plain LFM almost never says "I don't know" (1 of 10 never-told asks), so it misses y1t's bars for the same
  reason MiniCPM does.
- Suggested, not tested: trained doubt on LFM starts from more right answers (35), so it can lose up to 13 of them and
  still clear the 22 bar, where MiniCPM could lose only 4.
