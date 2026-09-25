# rd-371: a learned verifier replaces the min-token cutoff (one change)

Thread "Fix: reading facts from chat". Written 2026-09-25 09:54 UTC, before any verifier training, before readpanel371
was sealed or run. Plan and CPU preview: design/v3/30-modes/371-learned-checker.md.

## The one change
Which of the reader's structurally writable facts get saved. A: the live rule, min-token confidence >= 0.995.
B: a verifier (MiniCPM5-1B + its own LoRA, scripts/claude_rd371_verify.py) gives P(yes) that the turn states the fact; saved when
P(yes) >= T_B. Everything else is identical: the SAME reader reads (lis-301, the live 0.1 reader), the same compiler checks,
per-fact release (claude_lis318_score).
Verifier training: scripts/claude_rd371_data.py on the lis-318 reader training data (yes = agreed gold facts; no = plain-code
perturbations of the same turns: swapped roles, moved owner/value, other relation, non-saving mode shown as ASSERT, we -> me;
8,000 o0b positives max). LoRA settings as lis-318 (epochs 2, lr 2e-4, rank 32, batch 16, max-len 256, seed 300).
T_B: scripts/claude_rd371_sweep.py on lis-301's dev reads (959 turns): smallest grid value with 0 wrong-save turns, else the largest.
No DEV bank, panel, bank A/B, LoCoMo or LongMemEval text in any training row.

## Registered test
artifacts/claude-readpanel371-20260925 (TEST-ONLY; 240 turns, 411 facts; long multi-fact chat, role-swap traps, no-save turns;
written blind by a separate agent, blind second labeller, sealed before any rd-371 training). The reader reads it ONCE; both arms
score those same reads. Scorer: claude_lis318_score.py (owner + value match, counts only).

## Marks (fixed now)
| Mark | Bar |
|---|---|
| V1 more right facts saved: B saved_right | >= A's + 30 |
| V2 safe: B wrong_turns | <= 2 and <= A's + 1 |
| V3 no invention: B nofact_rows_with_save | <= 1 |
| G1 dev (lis-301 dev, all-or-nothing hits) | B at T_B >= A at 0.995 |
| G2 time: B median ms (reader + verifier) | <= A's + 400 |
PASS = all five. Proved wrong: B saved_right <= A's + 10 (the verifier does not recover right facts the cutoff throws away).
Report only: saved_right and wrong per kind, the per-fact dev curve for both gates.

Addendum 10:01 UTC, before any rd-371 training or run (description only; no bar changed): after the blind audit readpanel371
holds 240 turns and 426 facts (was 411; key fixes and 20 rewritten turns, second blind pass on the 28 changed rows). Final agreement:
426/426 gold facts, 8 extra labeller facts left out of the key, 233/240 rows. Seal: artifacts/claude-readpanel371-20260925/SEAL.sha256.txt.
