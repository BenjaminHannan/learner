# VERIFY k1c (Creative answers in chat thread, written 2026-09-26 17:18 UTC)

**k1c (the 1B picks among its own 4 drafts) = FAIL, on K1c.1.** C useful on 47 of 160, K (k1a, first passing draft)
on 46: C-only 12, K-only 11, sign p 0.50. Bar was +8 with p <= 0.05. The proved-wrong clause applies: K-only items
(11) are about as many as C-only items (12), so the 1B's own reading does not find the better draft; the DEV gain
(+3 of 40) was noise.

**The bigger finding: plain Qwen3.5-2B (114 of 160) and plain LFM2.5-1.2B (103) are far more useful on creative
requests than plain MiniCPM5-1B (46), on the same recipe.** Our writer (K 46, C 47) is level with plain MiniCPM5-1B and
far behind both rivals. Both rivals clear the K1 60% line (96); no MiniCPM5-1B arm comes close.

Run: rent-k1c, one RTX 5090, all ten runs (five arms x two panels) complete, seals, tests, DEV gate and V1 lines as
registered, $0.26 of $0.80 (RESULTS-rent.md on builder-outbox). Judging as registered (JUDGE-k1c.md): 800 replies
deduplicated to 716 distinct lines (A 448, B 268); judges 1 and 2 on all 716 (five blind agents each, chunks of at
most 150 lines), agreeing on useful for 675 and on made-up for 702; judge 3 on the 55 split lines. Scored with
scripts/claude_k1c_score.py (RESULTS-k1c.json); blind recount by a separate agent with its own script: see the last
section. Nobody who built k1c read a panel item or a test reply.

| Arm (160 items) | Useful | k1cpanel /100 | k1apanel /60 | Lead /105 | Made-up | Fallbacks | Bare list endings |
|---|---|---|---|---|---|---|---|
| C (k1a + the 1B's pick) | 47 | 24 | 23 | 31 | 10 | 0 | 7 |
| K (k1a) | 46 | 25 | 21 | 28 | 9 | 0 | 6 |
| T (plain MiniCPM5-1B) | 46 | 26 | 20 | 28 | 8 | 0 | 1 |
| Q (plain Qwen3.5-2B) | 114 | 71 | 43 | 78 | 6 | 0 | 0 |
| L (plain LFM2.5-1.2B) | 103 | 61 | 42 | 66 | 3 | 0 | 0 |

## k1c marks (C vs K, all 160 items)
- K1c.1 useful: C 47, K 46, +1; C-only 12, K-only 11, one-sided sign p 0.50. Bar >= +8 and p <= 0.05: **FAIL**.
- K1c.2 made-up replies: C 10, K 9. Bar C <= K + 4: pass.
- K1c.3 fallbacks: 0 and 0: pass.
Expected before running (DEV): C - K about +12, pass chance about 46%; if the pick does nothing, about 4%.
Got +1. C's reply differed from K's on 76 of 160 items; the changes were a wash.

## The K1 line (registered): FAIL
C useful 47 of 160, need 96 and >= T, Q, L. T 46, Q 114, L 103.

## Against same-size plain models (registered readings)
| | diff | first arm only | rival only | reading |
|---|---|---|---|---|
| C vs T | +1 | 24 | 23 | level |
| C vs Q | -67 | 6 | 73 | behind |
| C vs L | -56 | 9 | 65 | behind |
| K vs T | 0 | 25 | 25 | level |
| K vs Q | -68 | 7 | 75 | behind |
| K vs L | -57 | 7 | 64 | behind |
Q and L ran on the same plain recipe as T (the twin's system line, the whole chat, thinking off, greedy, <= 160 new
tokens), so the gap is the model, not our pipeline: our writer adds nothing over plain MiniCPM5-1B and loses nothing.
Made-up facts: Q 6, L 3, MiniCPM5-1B arms 8 to 10.

## Report only
- C - K by panel: k1cpanel -1 (6 vs 7), k1apanel +2 (6 vs 4); lead items +3 (10 vs 7), no-lead -2 (2 vs 4),
  uses_facts +1 (4 vs 3).
- Bare list endings are still MiniCPM-writer only (C 7, K 6; T 1; Q and L 0).
- On k1apanel alone K 21 and T 20 (the k1a run's judges gave 28 and 24 on the same items with different replies
  drawn on another GPU and another judge set): absolute counts move by several points between judge sets; paired
  comparisons inside one judging are what the marks use.

## What this means (inferred from the counts; nothing here was tested separately)
Picking among MiniCPM5-1B's drafts can't close K1: the model's drafts are the limit, and two other small models write
useful creative replies about twice as often. This affects 0.2d's K1 no-harm row (sealed 9ffe2e08f): a build whose
creative writer is MiniCPM5-1B will read "behind" Q and L by a wide margin. Which model writes creative replies is an
architecture choice, so it is Ben's.

## Blind recount
A separate agent wrote its own script (judges/recount_k1c.py) from the key, the three judges' files, the run rows and
the panels' kinds. It agrees on every count the marks and readings use: per-arm useful (C 47, K 46, T 46, Q 114,
L 103), per-panel useful, made-up (10, 9, 8, 6, 3), fallbacks (0), C-only 12 / K-only 11 / p 0.5, every rival pair,
76 differing C replies, judge agreement 675 and 702 of 716. It also checked that the keys cover each (arm, item) once
(800), that every arm under a line gave the same reply, and that judge 3 covers exactly the 55 split lines. Its
"lead" line used items with 2 or more earlier turns (34 items), not the scorer's 1 or more (105); that line is
report-only.

## Correction (added 2026-09-26 17:31 UTC, after the Thread manager's question; nothing above is changed)
"The model's drafts are the limit" in "What this means" is inferred, not measured, and overstated. Only the kept reply
was judged on the test panels; the runs did not save the 4 drafts. The one measurement of all 4 drafts is DEV
(artifacts/claude-k1d-20260926/PILOT-k1d.md: 40 chats, blind judges): at least one of the 4 drafts was useful on 26,
the first passing draft on 12, the 1B's own picks on 15 (k1c's P) and 14 (k1d's listener). So on DEV a useful draft is
often there and MiniCPM5-1B's own ways of choosing miss it. What the test panels show is narrower: with its first
passing draft or its own pick, the MiniCPM5-1B writer is level with plain MiniCPM5-1B and far behind plain Qwen3.5-2B
and plain LFM2.5-1.2B.
