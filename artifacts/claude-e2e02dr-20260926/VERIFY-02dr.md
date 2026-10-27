# VERIFY 0.2d-r: bank D memory rows with the right reader weights (Month-end, written 2026-09-26 17:21 UTC)

**Registered FAIL on H1 (wrong answers stated as fact: 12 vs 6, bar <= +2). All other rows PASS.** Under the
machine check fixed in ADDENDUM-02dr-machine.md, X' - G is **confounded by the machine**, so no row's difference can be
credited to the reader weights alone. The 0.2c verdict (FAIL) is unchanged. Since Ben's 16:04 Redirect, this is a report
on the old rule build only and is not an input to 0.2d.

Run: rent-02dr (instance 52763487, RTX 5090, 0.86 h, ~$0.43). Files republished to builder-outbox after the watcher
fix; all 25 match by sha256 (Director, artifacts/claude-republish-20260926g/FOLLOWUP.md). G and T are the reused 0.2c
files. X', G and T each covered the same 244 asks and 658 user rows (score/mechanical.json).

| Row | Test | Bar | X' vs G | Verdict |
|---|---|---|---|---|
| R0 | the wrapper refuses lis-301 weights and accepts lis-319 | both | refused on the Mac (READER-SHA-MISMATCH, exit 1); accepted on the rental | PASS |
| H1 | wrong answers stated as fact (M2), blind judges | <= +2 | 12 vs 6 (+6) | **FAIL** |
| H2 | turns with a wrong save (M1), blind judges | <= +2 | 17 vs 22 (-5) | PASS |
| H3 | never-told asks answered "don't know" (M5), scorer | >= -2 | 35 vs 33 of 36 (+2) | PASS |
| Y1 | answerable asks right (M4), scorer | >= +10 pts | 65 vs 44 of 195 (33.3% vs 22.6%, +10.8 pts) | PASS |
| ME1 | edit asks right (RIGHT + RIGHT_CONFIRM, as 0.2c counted), scorer | X' >= G | 5 vs 4 of 30 | PASS |

Judging, as registered: packets are X' and G mixed under neutral ids (seeds 3368 saves, 3369 asks;
judges/judge_prep02dr.py). There were two blind judges, each in its own private folder, and a third blind judge on the
splits only; keys were applied by script (judges/score_judges02dr.py).
- Saves: 513 packets, the judges agreed on 513, and 39 were judged wrong.
- Asks: 35 packets, the judges agreed on 33. The third judge called both splits wrong (one X', one G).
Nobody who built or scored the run opened the bank or a packet.

## Machine check (report only; rule fixed before the run)
Tr is the plain twin re-run on the rental, compared with 0.2c's T from BensPC:
- M4: 10 vs 15 (differs by 5).
- M5: 13 vs 12 (differs by 1).
- Edit: 0 vs 3 (differs by 3).
Two of the three differ by more than 2, so the machine effect is not small, and X' - G is confounded.
Suggested, not shown: the rental made the plain twin score lower, not higher.

## What the fixed readings say (as registered)
- H3: X' is 35, which is at least 31, so the 0.2c "don't know" drop (18/36) was caused by the wrong weights.
- Y1: X' is not within 5 of G (+21 asks), so in the old build part of the memory gap was a weights problem. This is
  confounded by the machine.
- H1 got worse, not better (0.2c: 8 vs 5). With the right weights the old build answers more memory asks, and it also
  states more wrong ones as fact.

## Deviations
- X' wrote 816 rows vs 0.2c X's 953; the ask and user-row counts match. This is unexplained.
- ep382_X.jsonl and sleep_Tr.jsonl were not written. Neither is a mark.
- Artifacts reached builder-outbox late because of a watcher publish bug (fixed; files sha-checked).

## Who gets what
- Y1 goes to Answering from memory.
- H3 goes to Making things up about you.
- H1 goes to Wrong answers stated as fact.
- The one-line verdict goes to the Thread manager.
