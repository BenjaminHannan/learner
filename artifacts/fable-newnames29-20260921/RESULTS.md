# Experiment 29 / M1-F10 "new names", 10,000 updates — results

Fable (coordinator) · 21 September 2026 · run once under FREEZE-NOTE.md (sha 638cc877…), source fingerprint
2a046e54…. Twelve runs, run integrity clean (12 runs, one source version, all full registered runs). Wave-1
verdict sealed in `wave1-verdict/` before wave 2 trained; unchanged by wave 2. Source tables: `report.txt`,
`gates.json`, `readouts/*.json`. Disclosures: `BUILD-NOTES.md` (no independent audit; GPT bridge failed).

## Registered verdict: PASS — arm F 3/3 seeds. Control 3/3 (not VOID). Not INVALID.

One change from experiment 27: 10,000 updates (learning rate held at 1e-3 to update 7,999) instead of 6,000.
Fresh seeds 2106–2108, fresh panels.

## Every seed, every cell (correct out of 512, never-trained names)

| Cell | Cutoff | Control | F (10,000; gated) | L (learned scale, 10,000; descriptive) | F6 (27's 6,000 recipe; descriptive) |
|---|---|---|---|---|---|
| c1 | 487 | 512/512/512 | 512 / 511 / 511 | 510 / 511 / 511 | 511 / 512 / 512 |
| c2 | 487 | 512/512/512 | 510 / 509 / 507 | 506 / 510 / 500 | 493 / 504 / 502 |
| c3 | 461 | 512/512/512 | 504 / 507 / 507 | 504 / 507 / 502 | 504 / 507 / 502 |
| c4 | 461 | 512/512/512 | 503 / 503 / 501 | 492 / 495 / 488 | 476 / 483 / 488 |
| c5 | 461 | 512/512/512 | 504 / 504 / 503 | 502 / 508 / 502 | 494 / 499 / 503 |
| c6 | 461 | 512/512/512 | 503 / 508 / 508 | 502 / 509 / 505 | 498 / 503 / 499 |
| p12-1 | 487 | 512/512/512 | 511 / 510 / 509 | 507 / 511 / 505 | 511 / 509 / 507 |
| p12-2 | 487 | 512/512/512 | 501 / 501 / 503 | 494 / 494 / 493 | 488 / 493 / 495 |
| p12-3 | 461 | 512/512/512 | 498 / 496 / 503 | 488 / 492 / 477 | 481 / 490 / 487 |
| s3 | 461 | 512/512/512 | 507 / 503 / 503 | 497 / 496 / 493 | 479 / 483 / 491 |

Paired mark (never-trained minus trained names, must be ≥ −13): F worst −11 (2106, p12-3); all 30 F cells pass.
L-2107 (−14) and L-2108 (−21) break it on p12-3; F6-2107 (−18) and F6-2108 (−15) break it on s3. So L 1/3 and
F6 1/3 on all marks, although every L and F6 cell cleared its cutoff.

Hand-computed descriptives (the wrapper's own overlay for these printed nulls — a reporting bug, no effect on
the verdict, which comes from 27's tested gate table):

| | F 2106/07/08 | F6 2106/07/08 | L 2106/07/08 |
|---|---|---|---|
| Total misses over ten cells | 67 / 68 / 65 | 185 / 137 / 134 | 118 / 87 / 144 |
| First-step link mistakes, 12-person cells | 2.54 % / 2.44 % / 1.66 % | 5.1 / 4.0 / 4.0 % | 4.0 / 3.7 / 4.6 % |
| 12-person ÷ 6-person mistake ratio | 2.9 / 2.9 / 1.7 | 1.5 / 1.7 / 2.2 | 2.7 / 4.6 / 2.4 |
| Open-set (all 4,096 codes) | 0.59 / 0.57 / 0.60 | 0.54 / 0.58 / 0.56 | 0.66 / 0.59 / 0.67 |
| Final name scale | 1.2 (fixed) | 1.2 (fixed) | 0.67 / 1.06 / 0.69 |

F and F6 share the same weights at update 4,000 in every seed (fingerprints equal), so F vs F6 is a clean
"same run, stopped early vs carried on" comparison. `undertraining_supported` needed all three F seeds ≤ 2.5 %:
F-2106 is 2.54 % (26 of 1,024), so the registered label is **unclear**, by one question. No late instability:
training link accuracy rose from 0.97–0.98 (updates 5,000–6,000) to 0.99–1.00 (9,000–10,000).

## What it means

- With the fixed name scale and enough training, the model binds never-seen names reliably: 3/3 fresh seeds,
  all ten cells, 496–512 of 512, no seed near a cutoff on the cell that sank experiment 27.
- Longer training is what did it: the same runs stopped at 6,000 updates (F6) make 2–3× as many mistakes and
  2 of 3 break the paired mark — experiment 27's partial result reproduced on fresh seeds.
- The fixed scale now beats the learned one. At 10,000 updates the learned scale drifted down to ~0.7 in two
  seeds and those arms kept a bigger new-name penalty. So "just start the dial high" (27's reading) is weaker
  than it looked; holding it fixed is the dependable recipe.

## What it does not mean

- Not open-vocabulary naming: choosing among all 4,096 codes is still only ~0.57–0.60 right. 16-candidate worlds only.
- Not perfect: F makes 65–68 misses per 5,120 questions where the control makes none, and never-seen names
  are still slightly worse than trained ones (mean paired difference −2.4 to −3.4).
- Crowding still costs: 12-person worlds have 1.7–2.9× the first-step mistake rate of 6-person worlds, and
  training never shows 12-person worlds.
- Seeds share training worlds (Q1 limitation). No independent audit of the wrapper script was obtained.
- Nothing about the dispatcher or the talker using new names.

## Predictions (hashed before any code; rows in `artifacts/fable-predictions-ledger.md`)

Mean Brier: reviewer 0.100 (19 scored rows, 1 void), coordinator 0.150 (8 rows). Both of us gave the PASS
under 0.45 (0.42 / 0.35) — we were too pessimistic after 27's surprise. Worst reviewer miss: "reserved_gap in
any coded run" 0.50 → FALSE (the failing L/F6 runs cleared every cutoff, so they are labelled `unnamed`).

## Next

M1 (new names, 16-candidate worlds) is met for the fixed-scale recipe. Per the loop directive, scale until it
breaks: larger worlds (16+ people) and the open-set pick are the obvious stress points; both need a fresh
registration. The wrapper's descriptive-overlay bug should be fixed before it is reused.
