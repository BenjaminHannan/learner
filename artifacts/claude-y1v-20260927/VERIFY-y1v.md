# y1v verify: NO-GO; the proved-wrong test does not fire (Answering-from-memory thread, 2026-09-27 20:47 UTC)

y1t's trained-doubt recipe on plain LFM2.5-1.2B-Instruct (commit 0f604ada), scored against PLAN.md (sealed in
SEAL.sha256.txt at main 37d05c9f9). The run was job rent-y1v-vast-p1, kit 37d05c9f9, results on builder-outbox
ce8469eac (artifacts/claude-y1v-20260927/run). RESULTS-vast.md says COMPLETE: all 4 steps rc=0, and 5 of 5 checks
passed. The card was one RTX 5090 at $0.5789/h. A first RTX 3090 create was gone after 6 minutes. Total $0.41 of the
$1.00 cap.

## Verdict (A1 on DEV; y1t's bars; counted from the rows files)
| model (same card) | answerable right (of 56) | answerable wrong-candidates | never-told "don't know" (of 10) |
|---|---|---|---|
| bar for GO | >= 22 | <= 8 | >= 8 |
| LFM + y1v adapter, merged | **39** (met) | **12** (missed) | **6** (missed) |
| plain LFM | 35 | 18 | 1 |

**NO-GO.** It misses the wrong bar by 4 and the "don't know" bar by 2.

**Proved-wrong test:** practice-dev never-told "don't know" rose from 22 to 136 of 145, a gain of 78.6 points
(train398r.json, dev_before and dev_after_lora). DEV never-told rose from 1 to 6 of 10, a gain of 5, which is not
fewer than 3. The test needs both, so it does not fire. Some of the trained doubt did carry over to other chats.

Rows: run/eval/y1g_rows.jsonl (sha256 a72f920c...) and run/eval_plain/y1g_rows.jsonl (sha256 ae1e3a72...). Both
sha256 values match the rental manifest. Each file has 71 asks, matched by (life_id, turn_index). This thread
recounted every number here from label_A1, and the counts agree with both eval logs. Plain LFM on this GPU gave
exactly y1u's CPU counts (35 / 18 / 1).

## Report (after the verdict)
- Kept: 32 of plain LFM's 35 right answers stay right. The other 3 became wrong answers, and 7 new ones became right.
- By ask type, right / wrong / "don't know" (trained; plain):
  - one_hop 13 / 3 / 0 (13 / 3 / 0)
  - two_hop 9 / 2 / 0 (6 / 4 / 1)
  - reversal 7 / 1 / 2 (6 / 3 / 1)
  - yes/no 4 / 2 / 3 (3 / 6 / 0)
  - edit 6 / 4 / 0 (7 / 2 / 1)
  - partial (not in the 56) 0 / 3 / 2 (0 / 5 / 0)
- Never-told: the trained model gave a made-up answer to 4 of 10 ("Ulla", "Xavi's last name is Xavi.", "Thea",
  "Viv"). The one ask plain LFM declined, it also declines.
- Other configs, report only:
  - trained: C3 35 / 8 / 7, C4 31 / 7 / 7, V 31 / 10 / 6
  - plain: C3 31 / 11 / 7, C4 29 / 9 / 7, V 23 / 10 / 8
  - None met all three bars.
- Drafts (drafts_log.txt):
  - LFM's greedy draft was right on 774 of 888 answerable training items. A sample fixed 38 of the others.
  - The training set had 1,654 rows: 827 answers (774 own greedy, 53 own sample) and 827 "I don't know." rows.
    Each row was used once, since there were more than 1,500 rows.
- Training: 207 steps; loss fell from 0.46 to 0.20. The adapter was 24 modules with 1,277,952 parameters, and all 24
  merged. Practice-dev overall went from 162 to 269 of 291. On value asks it went from 140 to 133 of 146, a small loss.
- Time: drafts took 11 minutes, training 5 and each DEV check 1. The adapter (sha256 cc34cce9...) was copied to the
  Mac and never pushed. RESULTS-vast.md labels the copy with the kit's default name ~/y1v-adapter; the job put it at
  ~/y1v-lfm-adapter.

## Predictions (made before the run)
| prediction | chance given | result |
|---|---|---|
| GO | 0.1 | no |
| right >= 22 | 0.8 | yes (39) |
| wrong <= 8 | 0.15 | no (12) |
| "don't know" >= 8 | 0.3 | no (6) |
| proved wrong | 0.3 | no |

## What this shows (labelled)
- Shown: on this bank, trained doubt on LFM beats plain LFM on all three counts, on the same card:
  - 4 more right (39 against 35)
  - 6 fewer wrong (12 against 18)
  - 5 more "don't know" (6 against 1)
  It still misses two of y1t's three bars.
- Shown: on LFM the recipe moved DEV more than it did on MiniCPM. y1t on MiniCPM went from 26 / 24 / 2 to
  22 / 20 / 5.
- Suggested, not tested: C3 on the trained LFM (35 / 8 / 7) is one "don't know" short of all three bars. It is not a
  y1v config, and this is not a verdict on it. DEV has only 10 never-told asks, so 1 is noise.

## Plain summary for Ben
The practice made LFM better at your memory questions on every count: more right (39 of 56), fewer made-up answers
(12, down from 18), and more "I don't know" (6 of the 10 things it was never told, up from 1). It still doesn't pass.
The bars were at most 8 made-up answers and at least 8 "I don't know"s. The run cost $0.41.
