# PASSMARKS 0.2d-r — bank D memory rows rerun with the right reader weights (registered 2026-09-26 ~13:10 UTC)

Owner: Month-end. Agreed with Reading facts (12:49 UTC 09-26, Ben's 12:48 rule on integrations).
Written and committed BEFORE any run. Sealed with SEAL-02dr.sha256.txt at registration; never edited after.
The 0.2c verdict (VERIFY-02c.md: registered FAIL) is NOT changed by this run, whatever it shows.

## Why
In 0.2c, bank D arm X ran the lis-319 reader code with the lis-301 weights (my task-file error, VERIFY-02c D1).
The wrong weights load without error. Rows H1, H2, H3, Y1, ME1 therefore did not test lis-319.

## One change
Arm X' = the 0.2c arm X, the same sealed code (artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt), the same
sleep adapter (run/sleep/adapter02c.pt, sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5,
sidecar-checked), with ONE difference: `--model` is the lis-319 merged reader
(model.safetensors sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76).
Launched through scripts/claude_readersha_wrap.py with READER_SHA set to that sha (new file; selftest 9/9).
G and T are NOT rerun: their 0.2c bank D files (origin/builder-outbox artifacts/claude-e2e02c-20260926/run/arm_G.jsonl,
arm_T.jsonl) are reused unread; G's 0.2c run used its own correct reader (lis-301).

## Marks (same rows and bars as PASSMARKS-02c.md)
| Row | Test | Bar |
|---|---|---|
| R0 | guard: the wrapper refuses the lis-301 weights (READER-SHA-MISMATCH before loading) and accepts lis-319 | both |
| H1 | wrong answers stated as fact (M2), X' − G, blind judges | ≤ +2 |
| H2 | wrong saves (M8a, turns with a wrong save), X' − G, blind judges | ≤ +2 |
| H3 | never-told asks answered "don't know" (M5), X' − G, scorer | ≥ −2 |
| Y1 | answerable asks right (M4), X' − G, scorer | ≥ +10 points |
| ME1 | edit asks right (ask_type "edit"), X' ≥ G, scorer | X' ≥ G |

0.2d-r PASSES only if every row passes. A FAIL stays a FAIL.
Report only: every other 336 mark; mechanical rows per ask type; confirm rows; facts saved; ms per turn;
the bm-398d answer-level check (Benchmarks' prep/score with evidence lines shown) on the Y1 asks, if its own
verdict is in by then.

## What the result would mean (fixed now)
- If H3 X' ≥ 31/36 (within 2 of G's 33): the 0.2c "don't know" drop (18/36) was caused by the wrong weights.
- If H3 X' ≤ 23/36: the drop is real with the right weights; the cause is in lis-319 or how build_02c hands the
  reader's notes to the answer step. Reading facts helps find which (agreed 12:49).
- Y1: 0.2c read 45 vs 44 of 195. If X' stays within 5 of G, the memory gap is not a weights problem.

## Judging (same as 0.2c, with the lesson from VERIFY-02c)
Blind opus judges get packets only: X' and G saves and asks mixed under neutral ids (new seeds 3368 saves,
3369 asks), keys applied by script. Two judges, each in its OWN private folder (no shared files), a third on
splits. The bank itself is never opened by judges or by me; only runners, scorers and the judge-prep script read it.

## Run
handoff/held/007r-02dr-benspc.md, on BensPC after 007b (and anything the Director orders first). $0. DISK: 1.
