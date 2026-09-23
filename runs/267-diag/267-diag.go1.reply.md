Fixing your QA checker builds — staging the diagnostic run.
Your 264 build is sealed as FAIL — now scoping the 267 follow-up diagnostic.
GPU is idle. Reading the remaining sealed modules.
Now checking how the 264 run reached BensPC, and reading the table + spec format.
Seal verified (120 lines, hashes OK) without opening content. Reading table + scorer code.
Scorer design clear. Checking 261b's report for the exact BensPC procedure.
BensPC needs a fresh script bundle. First, the table for C3's neighbour rule.
Smoke test caught two blind-safe fixes. Inspecting the pet row first.
C3 fixed. Writing predictions.
Predictions sealed. Opening dev.jsonl now.
C1 confirmed as prompt-B @ 0.25. Probing BensPC python + tokenizer base.
EncodedCommand channel works. Probing torch + base dir.
Writing the diag scripts.
Checkpoint hash matches. Copying the bundle.
Server PID 15380. Waiting for health.
VRAM shows Qwen resident. Rechecking health with simpler quoting.
Server healthy. Running the single ear pass (120 turns).
Ear pass complete (120 turns, ckpt verified). Fetching preds, building check batches.
C1 done (155, 0 fallbacks). Running C2.
All checker runs done. Fetching results, then stopping the server.
Same session-0 issue as 264 (D7). Force-killing the exact PID.
Unexpected numbers (C0 65 wrong, C1 held only 2). Digging into families and p-distribution before trusting this.
Decomposition is clear. Pulling the last diagnostic details (C3 plural picks, C1 holds, C2 fail split).
All details in hand. Assembling artifacts and writing the report.
Diagnostic complete. No panel run, no PASS possible — verdict is a comparison, not a grade.

**Verdict: diagnostic done, all three checkers scored on the same 155 ear frames.** C1 (YES/NO) kept all 90 good readings but caught only 2 of 65 bad ones — a rubber stamp on clean wording. C2 (QA) caught nearly all truly-bad readings (23 of 25) at a cost of 14 good ones. C3 (pick-1-of-4) matched C1 outside plural turns but blanked on all 14 plural frames, picking the other name 13 times. Absolute wrong-save counts are inflated for every arm by a dev gold-scope convention (below).

Marks table (integer counts, 117 TEACH + 10 ASK gold, 120 turns):

| Checker | TEACH hits | Held true | Wrong saves | per fact | per turn | ms med/p90 |
|---|---|---|---|---|---|---|
| C0 ear alone | 90 | 27 | 65 | 65/155 | 53/110 | 115/140 |
| C1 YES/NO @0.25 | 90 | 27 | 63 | 63/153 | 52/110 | 413/697 |
| C2 QA x3 | 76 | 41 | 31 | 31/107 | 30/110 | 1090/1952 |
| C3 pick-1-of-4 | 74 | 43 | 55 | 55/129 | 47/110 | 396/662 |

Every move and miss: C1 held 2 frames total (1 stale at p=0.04, 1 no-save at p=0.001), removed 0 true; C2 removed 14 true + 34 wrong (single-question fails: value 23, relation 20, owner 13); C3 removed 16 true + 10 wrong (picks: 129x1, 14x3, 7x4, 5x2, 0 fallbacks). ASK 9/10 all arms (ear's miss). Predictions: P267.1, .3, .7-bands, .8, .9, .10 right; P267.2, .4, .5, .6 missed and P267.7 order half-missed (C3 lowest, not middle) — all misses driven by the gold-scope effect plus C3's plural wipeout.

Deviations: D1 checkers run without span guard (sealed pre-dev); D2 C3 fixed reading order 1-4 (sealed pre-dev); D-GOLD dev gold excludes appositive-relative frames the 264 panel counts correct — 40/65 (C0), 40/63 (C1), 29/31 (C2), 39/55 (C3) of "wrongs" are truly-stated relative frames; non-relative wrongs are C0 25, C1 23, C2 2, C3 16. Server: started PID 15380 with 264's exact flags, stopped by exact PID (taskkill /F as in 264 D7), GPU idle 282 MiB, pythonw 13036 untouched. No earpanel* opened; dev opened only after the prediction seal (verified OK); 264's sealed files imported, never edited; all my files new.

What it means: on clean turns the YES/NO checker waves everything through; the question checker is the only one that kills real bad readings but taxes good ones; pick-one-of-four is fast and exact on plain facts yet one extra name in the turn breaks it completely.

What it doesn't mean: C1 isn't useless (the blind panel triggered it; this dev doesn't), C2 didn't win overall (same over-holding disease as 264), C3 isn't hopeless (fix multi-name turns first), and nothing here changes 264's registered FAIL.

Files: `artifacts/claude-diag267-20260923/` (PREDICTIONS.md, SEAL-pred.sha256.txt, REPORT.md, score.json, earpreds267.json, turns267.json, c1/c2/c3.json, checks/) and `scripts/claude_diag267_{c3,c3client,qbuild,score,turns}.py`.
