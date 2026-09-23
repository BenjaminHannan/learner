Fixing the diagnosis-driven follow-up — rebuilding the ear code with the boundary fix.
Load is high but workable; data reviewed. Setting up the follow-up files now.
Model diff is exactly the two intended hunks. Now the trainer shim and test pointer-swaps.
Files ready. Recording marks and predictions before the single registered run.
Pilot passes. Running the single registered test now.
All green. Writing the results record.
Verdict: PASS — own-O0d2, the one diagnosis-driven follow-up to the o0d FAIL, passes 5/5 marks on a single registered run (10 s wall clock, CPU only).

Marks table (integer counts):

| Mark | Bar | Result |
|---|---|---|
| Pown0d2.1 all 8 unit tests pass | 8/8 | 8/8 pass |
| Pown0d2.2 audit still exactly 32,850,051 | diff ≤ 0.005 | 32,850,051, diff 0.000000, all 7 parts exact |
| Pown0d2.3 kill test identical | sha256 equal at step 60 | A=054dbec63839 B=054dbec63839 (match o0d's hashes) |
| Pown0d2.4 fuzz 10,000 draws: 0 non-whole-word spans | 0 | 0/10,000 (span + owner checks) |
| Pown0d2.5 o0d smoke loss still falls (≤10 min) | last-10% < first-10% | 120 steps, 1.3347 → 0.3635, 2 s |

Every move: the 3 o0d failures (bpe-roundtrip, mask-blocks-cuts, decode-whole-word-only) now pass; the other 5 units still pass; audit exact; kill landed on ckpt_step30 and resumed byte-identical; fuzz 0 bad; smoke falls (identical numbers to o0d: 1.3347 → 0.3635); MLM 15-step pilot ran. Zero misses. No TEST-ONLY panel touched; toy data only, fictional names.

Deviations: D1 — the test's fuzz reference mask and round-trip call were updated to the corrected rule/signature (the o0d copies carried the same flipped condition / old signature, so keeping them would re-test the old bug, not the fix); documented in the test docstring. D2 — Pown0d2.1–5 predictions appended to the ledger plus PASSMARKS.md recorded before the run, per registration protocol. No other deviations.

What it means (plain high-school English): the one flipped condition was the whole problem. The ear can only point at whole words again, spaces come back when decoding, and nothing else moved — same size to the last number, same kill-and-resume hashes, same falling practice loss.

What it doesn't mean: it doesn't mean the ear reads English well. This was a code fix, not a training result — how well it reads real sentences is still untested and needs the later stages.

PUSH: artifacts/claude-own-o0d2-20260923 scripts/claude_own_o0d2_model.py scripts/claude_own_o0d2_test.py artifacts/fable-predictions-ledger.md (plus scripts/claude_own_o0d2_train.py, the new trainer shim, on disk for the watcher).
