# English with generated practice questions: pass marks (fixed 2026-10-04 before any training run)

Ask: coordinator relay 03:47 UTC 10-04. Train the round-3 setup on many generated English questions of the six kinds, with 6 paired seeds and marks fixed first. Make the bare 1.2B LM an explicit comparison row, because beating it is the real bar. The cap is about $2.5.

- **One change from round 3:** the training rows. Round 3 trained on the pilot bank alone (96 rows). Round 4 adds 8000 generated examples per seed (`gen_english.py`, `--gen 8000`, generator seed 1000+seed). That is 32,000 rows, drawn as source/paraphrase × 2 questions. Everything else is the same: the code path, the allptr arm, 2000 updates of 16 rows, lr, and seeds 0 to 5. The comparison is paired with round 3's allptr runs (`../english/results/box*/out/allptr-seed*.json`).
- **Fresh test:** unchanged, `FRESH-EN-R3.json` (sha256 9e0ca5b5b069…, 192 questions). The generator's pools exclude every capitalised word in the fresh file and every word inside a fresh answer. The runner asserts that no generated text equals a fresh text.
- **Generated held-out panel (read only):** `GEN-HELDOUT-R4.json` (sha256 25b4e951d289…). It has 48 examples built from held-out names and nouns: 20% of each pool, never used in training.
- **Bare-LM rows:** these use the same frozen 1.2B instruct model with no trained parts and are deterministic, so each runs once.
  - lm_alone (zero-shot, round 3): 29.7% exact.
  - lm_fewshot (8 bank examples as chat turns, run this round).
  - The **bar** is the higher of the two exact scores.

## Judged 1: allptr-gen minus allptr (round 3), fresh exact accuracy over all 192
- **PASS:** a mean of at least +15 points, with the 95% t-interval's lower bound above 0 (df 5, t = 2.571).
- **FALSIFIED:** a mean below +5.

## Judged 2, the real bar: allptr-gen against the best bare-LM row, fresh exact accuracy
- **PASS:** a mean of at least the bar plus 10 points, with the lower bound of the interval of (seed score − bar) above 0.
- **FALSIFIED:** a mean at or below the bar.
- **In between:** a mean above the bar but short of the PASS line.

## Read, not judged
- "contains" accuracy against lm_alone's 76%.
- The generated held-out panel.
- Per-family results.
- Train fit on the bank.
- The zero-pool core lesion.
- The share of wrong answers that equal a bank answer.
