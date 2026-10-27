# Exp 235b PASSMARKS -- a write gate on the unchanged 235 ear (sealed before the 235b panel is opened)

ONE CHANGE vs 235: a write gate after the brake. Same frozen checkpoint (sha256
`2852a5c0d60b2ef361cbf45eb14863b0047b56bd89e65fa90db4479ddf3fd8f8`, artifacts/claude-smolear235-20260922/train/CKPT.sha256.txt,
kept on BensPC). No retraining, no new training data, brake unchanged. Greedy reading = the 235 reading.

## The gate (scripts/claude_smolear235b_beam.py `gate`)
- k-best: beam search, k = 4, summed token log-probs of the whole output (no length normalisation), own torch code
  (batch-4 CUDA graph on the GPU, eager on CPU). Beams are computed only when the brake keeps a TEACH frame and the
  turn does not end in "?" (otherwise the gate has nothing to decide).
- (a) question guard: turn ends in "?" (after trailing spaces/quotes/brackets) -> no TEACH saved (GUARD_Q);
  another valid top-k decode within tau of the greedy one containing an ASK frame -> UNSURE_ASK.
- (b) margin gate: a TEACH frame f is saved only if lp(greedy) - lp(best competitor) >= tau. Competitor = a top-k decode,
  other than the greedy text, whose normalised frame set lacks f (f changed in act/subject/relation/value, or absent).
  Only VALID readings compete: a decode with any frame the brake would drop (non-span subject/value, relation not in
  table, malformed) is ignored (a NONE decode is valid). Same frame = the 235 scorer's normalisation. Duplicate texts:
  the best lp. No valid competitor in the top-k -> margin = +inf (saved).
- Otherwise UNSURE (not saved; counted separately; a later loop version would ask the user to confirm).

## tau (chosen on my own dev set only; the 235b panel not opened)
Dev = 900 rows of the 235 held-out-template dev split + 240 new risk rows in my own wordings
(R1 pronoun 90, R2 statement-shaped questions 70, R2s question-word statements 20, R3 verb-decides-relation 60).
The brief's rule: the most recall at <= 1 % wrong saves (per non-question dev row). **No tau on the grid 0-15 reaches 1 %**
(floor 15 wrong / 867 = 1.7 %, from confident errors whose top-4 holds no valid competitor). Fallback, fixed here before
the seal: the tau with the LOWEST wrong-save rate, ties -> the smallest tau. **tau = 11.8** (dev/tau.json).
Dev at tau = 11.8 (A = gate) vs A_brake (the 235 arm):
| dev slice | A_brake hit/gold, wrong | A hit/gold, wrong, UNSURE |
|---|---|---|
| all | 611/669, 87 | 338/669, 15, 301 (+44 GUARD_Q) |
| base (235 dev) | 428/434, 5 | 270/434, 2, 137 |
| R1 | 129/155, 20 | 62/155, 4, 83 |
| R2 (gold NONE) | -, 36 | -, 3, 13 (+20 GUARD_Q) |
| R2s | 20/20, 0 | 2/20, 0, 18 |
| R3 | 34/60, 26 | 4/60, 6, 50 |
Pilot on a 150-line fixture built from my dev rows in the panel schema: A M3 49/99, M2 2, M3b 44 %, M4 39/40, GPU median 154 ms.

## Panel + scoring (scripts/claude_smolear235b_score.py; loader scripts/claude_smolear235b_panel.py)
Panel artifacts/claude-earpanel235b-20260922/panel.jsonl (panel seal checked before use). Strict schema check -> exit 3
(SCHEMA-MISMATCH, nothing scored). The 235 chain-gold fix is inside the loader (two-hop gold = `chain`, aliases on the last
hop). `clear` ignored (clear:false counts fully). Matching = the sealed 235 functions. Arm B = 138i + 228
(scripts/claude_smolear235b_armb.py -> claude_smolear235_armb.run_items), statement families only.
Arms reported: A_raw, A_brake (= the 235 arm), A (registered), B; per family and per tag (R1/R2/R3).

## Marks (A = ear + brake + gate)
| mark | bar |
|---|---|
| M1 | no_save: TEACH frames saved <= 1 |
| M2 | wrong saves across plain_teach + varied_teach + full_names + corrections + no_save <= 1 |
| M3 | exact TEACH recall on plain_teach + varied_teach + full_names + corrections >= 85 %, and >= B + 30 points |
| M3b | UNSURE TEACH frames (margin + ASK-within-tau) on those 4 families <= 12 % of their gold TEACH frames (GUARD_Q reported separately) |
| M4 | exact ASK recall on questions + chain_questions >= 90 % |
| M5 | median GPU ms per turn (greedy + brake + beams + gate) <= 300; Mac CPU (1 thread) reported, no bar |
Registered verdict PASS only if all six pass.

## Predictions (also in the ledger)
- P235b.1 M1 passes (0-1 saves), ~85 %.
- P235b.2 M2: 1-4 wrong saves; pass ~35 %.
- P235b.3 M3: A recall 40-60 %: FAIL (~97 %). A_brake 85-95 %.
- P235b.4 M3b: UNSURE 30-50 %: FAIL (~95 %).
- P235b.5 M4 passes (>= 90 %), ~85 %.
- P235b.6 M5 passes (median 120-200 ms).
- P235b.7 Overall registered PASS ~1 %. The gate trades recall for safety; it cannot see confident errors.
