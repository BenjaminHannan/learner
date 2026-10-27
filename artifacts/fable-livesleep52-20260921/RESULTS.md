# Experiment 52 — Live sleep: install episodes mined from real 200-turn logs

**Registered seeds 5201, 5202, 5203. Sealed PASSMARKS before the wave. SCORE: PASS (6/6 marks).**

## What ran

For each seed, a deterministic generator produced a 200-turn conversation log against a
freshly trained Exp 44 base (all three bases: fresh 1–3 = 1.00, fresh depth-10 = 1.00,
big depth-10 = 1.00, unknown rate = 1.00 — no VOID). The log carries village ask/confirm
teachings plus realistic noise: 28 small-talk, 6 teach turns (3 DUPLICATE_OK, 3 CONFLICT),
8 ambiguous asks, 8 unanswered asks, 4 unconfirmed asks, 4 stray confirms, 6 corrections,
and a decoy chain (mother→father) confirmed 8 times.

A pure-rule miner (never the model) replayed the log through five rules — STATUS (only
OK asks), PAIR (immediately-adjacent confirm, same pair_id), SUPERSEDE (latest correction
wins), FALL-THROUGH (anything between ask and confirm breaks the pair), ANSWER-IN-VOCAB —
then applied the frequency rule: chain length ≥ 2 and ≥ 20 standing confirmed episodes →
candidate, visited in sorted order, refused if no matching word slot.

Each night was one corruption level (0/2/4 standing wrong teachings per chain). The miner
found exactly 3 candidates × 20 standing in every log; the decoy chain was counted at 8
and refused. Each candidate was installed via Experiment 46's recipe imported unchanged
(`import fable_hardgate46`): robust loss −log((1−ε)p+ε/N), ε=0.10; router hardened to
argmax chain ±30 logits after each fold fit and the refit; 4-fold gate OOF ≥ 0.80, refit
agreement ≥ 0.90, base answers unchanged, weights-only reload identical; then the 60-start
audit on `rec["path"]`. Wrong install = installed AND (audit disagreement > 0 OR fresh
accuracy < 0.99).

## Marks (per-seed integers, never averaged)

| Mark | Threshold | Result |
|---|---|---|
| M1 zero wrong installs | 0 of 27 | **PASS — 0 wrong of 27** |
| M2 installs at ≤ 2 standing-wrong | ≥ 15/18 (brief's 12/15 scaled to 80% of 18) | **PASS — 18/18** |
| M3 taught facts + prefix + chain | 100% over 9 sleeps | **PASS — 9/9** |
| M4 each sleep() < 600 s | max < 600 | **PASS — max 7.3 s** |
| M5 miner exact | 9/9 logs | **PASS — 9/9** |
| M6 old skills bit-identical | 9/9 sleeps | **PASS — 9/9** |

Per seed, installs (made/attempts) by standing-wrong level:

| Seed | 0-wrong | 2-wrong | 4-wrong |
|---|---|---|---|
| 5201 | 3/3 | 3/3 | 3/3 |
| 5202 | 3/3 | 3/3 | 3/3 |
| 5203 | 3/3 | 3/3 | 3/3 |

Totals: 27/27 installed, **0 wrong installs**, manipulation check true on all 9 nights
(standing-wrong per chain == the night's level).

## What was proven

1. **M1 (clean stays clean).** Even at 4 standing-wrong teachings per chain, the 60-start
   audit and 0.9 fresh-accuracy threshold never let a wrong install through: 0/27.
2. **M2 (noisy mostly works).** At ≤ 2 wrong, 18/18 installs passed (threshold 15/18).
   Even the 4-wrong level got 9/9 — the robust loss + fold gate + audit absorbed the noise.
   The margin exists but was not needed; this is a safe-direction result.
3. **M5 (miner is exact).** All five rules plus the frequency threshold fired precisely as
   specified on all 9 logs: 3 candidates × 20 standing, decoy refused at 8, 6 supersessions,
   68 standing total, no episode from a non-OK ask, no episode from small talk or unanswered
   turns.
4. **M3 + M6 (sleep is additive).** Every sleep appended exactly one `sleep-derived` report
   row; taught facts (fact-id, subject, relation, value, active) compared identical; the
   pre-sleep `events.jsonl` remained a byte-exact prefix; fresh reload verified the hash
   chain (event count +1, last-hash match, no LogCorrupt); token-routing table byte-equal
   to the original base; 900-question base probe answer-for-answer unchanged; in every
   saved install, every parameter except the target word slot was byte-equal to the frozen
   wake snapshot.
5. **M4 (wall-clock).** Slowest sleep 7.3 s — three orders of magnitude under the 600 s cap.

## Given by hand (not learned)

Miner rules and the ≥ 20 threshold; the Exp 46 recipe (loss form, ε, hardening ±30, gate
constants, audit, wrong-install definition); the three word slots and chains; the 0.9
threshold, hop loop, lookup matrices (Exp 44, unchanged); the generator's noise counts and
which slots were corrupted.

## Predictions (ledger P214–P218, written before the wave)

- P214 M1: predicted pass at 85% → **outcome PASS**.
- P215 M2: predicted pass at 75% → **outcome PASS** (18/18, better than the 15/18 bar).
- P216 M5: predicted pass at 90% → **outcome PASS**.
- P217 M3+M6: predicted pass at 95% → **outcome PASS**.
- P218 M4: predicted pass at 97% → **outcome PASS** (max 7.3 s).

All five predictions resolved TRUE; no v2 needed.

## Files

`scripts/fable_livesleep52.py` (miner, generator, notebook builder, LiveSleeper, driver,
score, selftest — selftest 34/34 on throwaway seed 9999); this directory: PASSMARKS.md,
SEAL.sha256.txt, wave.sh, runs/ (per-seed logs, scores, install cells, sleep reports),
RESULTS-SEAL.sha256.txt; `design/v3/30-modes/52-live-sleep-opus.md`.
