Starting the dual-lane GPU run — fetching latest handoff and scoring guides.
Rules and scoring bars loaded — now checking for prior results and available credit.
No duplicate jobs pending — now hunting down the adapter hashes and rental options.
Cheapest reliable 5090s spotted — verifying specs and BensPC adapter access.
Adapter hashes recorded — now renting the GPU.
Fallback writer hash confirmed — waiting for the rental to boot.
Rental is running — testing SSH and starting the file transfer.
Adapter verified file-for-file — launching environment setup.
Environment passes — downloading base models.
All seals verify — running self-tests.
Self-tests pass — fetching data and building dialogs.
Data ready (2760 turns) — rebuilding the writer and running the smoke test.
Smoke passes (4/4 rows with questions) — launching both long writes in parallel.
W2 is running; Q2 failed on a path issue — relaunching it correctly.
Both lanes running in parallel — entering the monitoring loop.
Good pace (Q2 at 1100/2760, W2 growing) — continuing to monitor.
W2 finished (2760 turns) — waiting on Q2's final rows.
Both writes complete — launching both score steps.
W3 scored; Q3 hit the same path quirk — relaunching with absolute paths.
W3 shows a strong B lift — waiting on Q3.
Q3 done (A matches W3's A exactly) — launching the two v3 rescores.
All compute finished — verifying result files before copy-back.
All hashes match — confirming the last two, then destroying.
Rental destroyed — now computing the results tables.
Verdicts computed (W passes L1–L3, Q fails) — writing the two RESULTS files.
Files are gitignored like all artifacts — force-staging the PUSH set for the watcher.
Verdict: lane W (rd-378L) PASS — L1, L2, L3 all pass, proved-wrong not triggered. Lane Q (rd-379q) FAIL — Q1, Q2, Q3 all fail, proved-wrong clause holds. Both lanes ran to completion on one shared rental; nothing is left running.

Marks table (fused, categories 1-4, n=759, integer counts):

| Lane | Mark | Bar | A | B/Q | Diff (points) | Result |
|---|---|---|---|---|---|---|
| W | L1 | B any@10 ≥ A+5 | 496 (65.3%) | 583 (76.8%) | +11.5 | PASS |
| W | L2 | no cat >3 below A | — | c1 +17.7, c2 +5.8, c3 +18.2, c4 +10.8 | worst +5.8 | PASS |
| W | L3 | B anyT@10 ≥ A+5 | 496 (65.3%) | 577 (76.0%) | +10.7 | PASS |
| W | proved-wrong | B ≤ A+1 | — | 76.8 vs 66.3 | — | not proved wrong |
| Q | Q1 | Q any@10 ≥ A+5 | 496 (65.3%) | 431 (56.8%) | -8.5 | FAIL |
| Q | Q2 | no cat >3 below A | — | c1 -7.1, c2 -16.7, c3 -6.8, c4 -6.2 | worst -16.7 | FAIL |
| Q | Q3 | Q anyT@10 ≥ A+5 | 496 (65.3%) | 437 (57.6%) | -7.7 | FAIL |
| Q | proved-wrong | Q ≤ A+1 | — | 56.8 vs 66.3 | — | proved wrong holds |

Compliance with the first-13-lines rules (reporting as instructed): additive only — created new files (2 RESULTS.md, 6 result files, 2 private dirs' contents, 1 ledger line via cat >>), never edited or deleted anything; fictional names only (only made-up smoke names shown); no secrets printed (key read only as $(cat …), never shown); TEST-ONLY panels never touched; every move and miss reported here. One deviation: two background launches failed on first try with a wrong working directory (my `&` chained the `cd`), both relaunched correctly — `ps` checked before each retry, each step ran once.

Key reports: COMMIT cd91474c676364c3e4d0ccfa6faf2542d447eb1c. Credit balance number: 8.599180226269851. Import check: `2.11.0+cu128 5.17.0 0.21.0 NVIDIA GeForce RTX 5090 torchvision None`. GPU RTX 5090, instance 52770443 (label claude-notes-rd378Lb), ~0.93h × $0.5037 ≈ $0.47 of the $1.30 budget (rentals used: 1 of 4). Seals: SEAL-E 14/14, SEAL-D 13/13, SEAL-C 4/4, SEAL-B 13/13, SEAL 9/9, all OK; all 4 selftests PASS. DATA: locomo10.json hash matched, dialogs {"turns": 2760}. W1 JSON: {"sha256": "dbcc8db5…88510", "match": true, …} with separate sha256 confirming dbcc8db5 (rebuild route, adapter hashes matched BensPC file-for-file, no fallback). W2: "wrote notes for 2760 turns on cuda" (notes 2556, unparsed 33, median ms 346.2, p90 635.2). Q1 smoke 4/4 rows with questions (shown in RESULTS). Q2: "wrote questions for 2760 turns" (8265 questions, 1 empty turn, median ms 358.8, p90 513.5). Q3's store A equals W3's store A exactly (sanity holds). V3 report-only: A 520/520, Q 468/482, fact-B 578/581 (any@10/anyT@10) — fact notes hold their gain on v3 (+8.0 points anyT), question notes sit below v3 A+2. Copy-back: all 14 files sha256-verified on both ends before destroy; destroy confirmed (`still_there=False`); one ledger line appended; 9 PUSH files staged. Mean fused turns@10: A 10.00, B 9.97, Q 9.03.

What it means in plain English: the fact-writing notes genuinely help the search find the right message — 87 more questions found out of 759, in every category, even with a strict same-number-of-messages budget. The question notes, which were supposed to be a safe alternative that can't state anything false, actually make search worse than showing no notes at all. So the "avoid the truth problem by asking questions" idea is dead; since fact notes passed, the registered next step is 4b (the cut-only fact writer) only if fact notes beat question notes on anyT@10 by more than 5 points — they do (577 vs 437 = +18.4 points), so 4b is worth its cost.
