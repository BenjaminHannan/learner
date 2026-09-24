Starting your rental run — fetching the latest specs and marks.
Got the task spec and rental rules — now pulling the verification docs.
No duplicate run found — setting up the rental GPU next.
Credit and setup verified — building the code tree for the GPU.
Tree is packed — searching for a GPU rental now.
Found a cheap RTX 5090 — renting it now.
Rental is running — uploading code and setting up the environment.
Environment ready — running seal checks and validation tests.
Pre-checks passed — launching the full registered run.
Runs finished — verifying outputs and pulling results back.
All files verified — destroying the rental and writing up results.
Results written — appending the ledger entry.
VERDICT: RAN — the REGISTERED runs of 333b and 333c both completed on 1 rental, all files copied back and hash-checked before destroy. P333.1 PASS for both; P333.2 FAIL for both (17/30 and 26/30 vs bar ≥ 29/30). P333.3–P333.5 need the thread's blind judges.

Marks table (integer counts, bars from PASSMARKS.md):

| Mark | Bar | 333b (run-b) | 333c (run-c) |
|---|---|---|---|
| P333.1 notebook events on creative turns | 0 | 0 PASS | 0 PASS |
| P333.2 controls equal to B | ≥ 29/30 | 17/30 FAIL | 26/30 FAIL |
| P333.3 creative on-topic and useful | ≥ 32/40 | not judged here (packet in run-b/judge_creative.jsonl, unopened) | not judged here (packet in run-c/judge_creative.jsonl, unopened) |
| P333.4 invented person-facts | ≤ 2/40 | not judged here | not judged here |
| P333.5 P preferred or tied vs T | ≥ 20/40 | not judged here | not judged here |

Report-only counts: 333b routed 13/30 controls and 25/40 creative, 0 fallbacks, median 959.7 ms/creative turn. 333c routed 4/30 controls and 25/40 creative, 0 fallbacks, median 901.3 ms/creative turn. Think-text rows: 0 in run-b/arm_P.jsonl, 0 in run-b/arm_T.jsonl, 0 in run-c/arm_P.jsonl (expected 0/0/0).

Every move:
1. `git fetch -q origin main builder-outbox` ok. Read the queue spec, all of 330-rent-kit.md, VERIFY-333.md, PASSMARKS.md, PASSMARKS-333b.md, PASSMARKS-333c.md via `git show origin/main:<path>`.
2. DUPLICATE check: no `run-b` under origin/builder-outbox `artifacts/claude-cre333-20260924/` (only `run/`, `run-twinb/`) — proceeded correctly. No live instance labelled rent-333bc-creative. Credit $5.31 vs $1.00 budget.
3. Built the code tree per the kit (builder-outbox archive + main archive, main on top; self122_head.pt sha 5ca02173… match; 157 MB tgz) and rented 1× RTX 5090 (offer 48989513, contract 52457249, dph $0.5037; search re-run right before create; `success: true`).
4. Setup on rental: image torch 2.8.0+cu128 CUDA True; pip installs env-only; BASE snapshot commit 87179e5c… matches expected; smoke test `S.route122` returned without raising. All steps under setsid/nohup with logs.
5. Step 1: panel `sha256sum -c SEAL.sha256.txt` 3/3 OK; `claude_cre333b_test.py` printed "333b/c tests: 2/2 OK …"; SEAL-code-333bc.sha256.txt written BEFORE running (6/6 scripts).
6. Step 2, each its own process with full PANEL/D paths: first lines `cre333b: …` (b P, wall 57 s), `cre333b: …` (b T, wall 112 s), `cre333c: …` (c P, wall 37 s) — all started correctly, exit 0.
7. Step 3: exact `cp` commands; arm_B sha ddc490cf… identical before/after and in both run copies (unchanged); both `--score` runs exit 0 (~0 s each).
8. Step 4: mechanical `<think` counts 0/0/0, no reply read or quoted; judge files never opened.
9. Copied all 13 files back; local sha256 matches remote for all 13. Destroyed instance 52457249 (0 rent-333bc-creative live after; siblings untouched). Ledger line appended with `cat >>`.
10. Wrote RESULTS-333bc.md (summaries, PASS/FAIL vs bars, counts, GPU/hours/dollars/commit/walls, no replies quoted).

Misses/deviations: none on procedure. Two observations, not deviations: wall times differ from the 333 run (T arm 112 s here vs 311 s there — different code path, twin b); the instance ran ~4 min before `running` (within the 6-min rule). Spend ≈ $0.14, under budget. One rental used of 4 allowed.

What it means in plain English: turning the generator's thinking mode off fixed the fallback bug — both variants produced real creative replies every time (0 fallbacks vs 25 for 333) with zero stray thinking text. 333c's stricter request detector cut wrongly-routed controls from 13 to 4 while still catching all 25 creative requests, but 4 wrong routings still fail the near-perfect (29/30) bar, so P333.2 FAILs for both. Whether the replies are actually good, truthful, and better than the plain twin (P333.3–P333.5) still needs the blind judges — this run only delivers the sealed packets for that.

PUSH: artifacts/claude-cre333-20260924/RESULTS-333bc.md artifacts/claude-cre333-20260924/SEAL-code-333bc.sha256.txt artifacts/claude-cre333-20260924/run-b artifacts/claude-cre333-20260924/run-c artifacts/fable-predictions-ledger.md
