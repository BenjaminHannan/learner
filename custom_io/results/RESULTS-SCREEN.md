# Screen results: custom reader/reasoner/talker designs vs same-size transformers (2026-10-05)

Marks: `custom_io/PASS-MARKS.md` (fixed before training). Full verdicts and per-seed numbers:
`SCREEN-ANALYSIS.json` (from `python3 -m custom_io.analyze --stage screen`). Every arm is trained from scratch on the same
200k seed-1 skills rows, in the same order (seeds 100 and 101), 24,000 updates, batch 256, lr 1e-3, bf16, on Vast RTX 5090s.
Dev splits only (fast lane); nothing touched GOLD-PRIVATE, reserved or blind panels. Labels: shown = measured here.

## Scores (exact match %, shown)
| run | params | pooled-5 | in_dist | answer | frame | vocab | variant | held-out families | chain-5 |
|---|---|---|---|---|---|---|---|---|---|
| tf_s100 | 3,244,544 | 53.8 | 73.8 | 41.8 | 70.2 | 64.0 | 21.1 | 2.5 | 33.6 |
| tf_s101 | 3,244,544 | 54.9 | 77.5 | 43.4 | 72.2 | 62.8 | 19.5 | 1.2 | 34.8 |
| tfsteps_s100 | 3,260,928 | 68.4 | 87.0 | 62.3 | 83.2 | 80.4 | 32.2 | 0.6 | 93.5 |
| C1' (tfsteps_s100 + calculator) | same | 69.4 | 87.8 | 64.1 | 83.9 | 81.0 | 33.1 | 0.6 | 96.3 |
| tfsteps_s101 | 3,260,928 | 67.1 | 87.9 | 61.8 | 83.1 | 78.8 | 26.8 | 0.6 | 94.2 |
| C1' (tfsteps_s101 + calculator) | same | 68.4 | 89.3 | 63.4 | 84.4 | 79.9 | 28.0 | 0.6 | 96.5 |
| A_s100 | 3,217,708 | 64.2 | 84.1 | 57.8 | 83.4 | 72.9 | 24.3 | 2.5 | 63.3 |
| A_s101 | 3,217,708 | 64.8 | 84.6 | 55.9 | 84.3 | 76.0 | 25.6 | 0.6 | 62.9 |
| A0_s100 | 3,217,708 | 61.0 | 82.9 | 53.1 | 78.9 | 71.0 | 21.0 | 0.0 | 43.6 |
| A0_s101 | 3,217,708 | 60.0 | 80.0 | 53.6 | 77.8 | 68.2 | 22.1 | 1.9 | 43.1 |
| B_s100 | 3,252,368 | 68.3 | 84.3 | 69.6 | 78.8 | 83.1 | 30.8 | 1.9 | 99.7 |
| B_s101 | 3,252,368 | 68.8 | 86.2 | 70.0 | 77.1 | 82.6 | 33.0 | 4.4 | 99.5 |
| l2x2_s100 | 1,665,024 | 48.8 | 70.8 | 36.2 | 64.0 | 56.6 | 17.0 | 1.2 | 26.9 |
| l2x2_s101 | 1,665,024 | 49.1 | 70.3 | 39.3 | 63.0 | 55.6 | 17.9 | 0.6 | 25.6 |

For scale (not the same model class): the current 1.2B sandwich scores 74.6 on the same in_dist split (one checkpoint,
eval bug corrected). Every arm here is about 0-4% on held-out families, as forecast.

## Verdicts (2-seed means, paired by seed)
- **A (register loop): NO-GO.** pooled-5 +10.1 vs plain_tf, chain-5 +28.9, but -3.3 vs plain_tf_steps (G4 fails).
  Evidence: the loop matters (A - A0 chain-5 +19.7; prompt-blind after round 1 puts chain-5 at 0.5-1.1), but the
  round-1 register interchange matches the counterfactual on 1.8% of rows (mark 40): the rounds recompute from the prompt
  instead of carrying the intermediate value. That is the "proves A wrong" result written in advance (cf < 15).
- **A0 (A without step targets): NO-GO.** -7.2 vs plain_tf_steps. loops:1 keeps chain-5 at about 40 (mark <= 15).
- **plain_tf L2x2: NO-GO.** -5.4 vs plain_tf.
- **B (Ledger: planned steps + exact executor): NO-GO by the letter.** G1-G4 pass: pooled-5 +14.2 vs plain_tf, +0.8 vs
  plain_tf_steps, -0.3 vs C1'; chain-5 +65.4 (99.5-99.7). Evidence marks hold: loops:1 chain-5 0.5-2.3; noexec puts the
  program families at 0.4-1.0; ADD/SUB swapped in the executor gives the swapped program's value on 99.9% of rows.
  G5 fails on one wiring check in both seeds: donor_match on string families. B answers those by pointing into the prompt,
  so a donor's state copies the recipient's own word; the check cannot pass for that talker. Also failed: "loops:2 keeps
  one-op families within 5" (they fall 90-94 points; the mode and answer pointer are read after the last of 8 trained
  iterations, so a 2-iteration run breaks the readout as well as the program).
- **The strongest baseline is plain_tf_steps** (a 3.26M char transformer that writes the worked steps): in_dist 87-88,
  13 points above plain_tf and the 1.2B sandwich.

## Where B loses (shown, diagnosis on B_s101's checkpoint with `custom_io/diag_ledger.py`)
The talker picks the right mode on almost every row; rows are lost inside the non-program paths: GEN registers cannot
emit an answer char they never emitted in training (letter_ops answer split 0/40, digits_parity answer 0/40), and the
content-free WORD pointer misses in new sentence frames (copy_word frame 22/40, group_induct frame 19/40). Next design:
B2 (`custom_io/design/design-B2.md`, marks in PASS-MARKS addendum 2).
