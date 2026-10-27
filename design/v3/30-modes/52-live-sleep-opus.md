# Mode 52 — Live sleep: mining install episodes from real conversation logs (Experiment 52)

## Problem

Experiment 46 proved an install recipe (robust loss, hardened router, fold gate, reload
check, 60-start audit) but only on clean toy episodes handed to it by the experiment. A
live model never receives hand-built episodes: it receives **conversation logs** — turns of
asks, confirms, corrections, noise — and something must decide, mechanically, what to train
on. The brief's rule stands: *sleep is automatic and mathematical*. The model never
proposes rules and never chooses what to store.

## Design

Three pieces, all pure functions of the log:

1. **Generator (fixed, documented).** Produces an exactly-200-turn log per night against a
   fresh Exp 44 base: 60 teach pair-turns (20 per word chain), plus declared noise —
   28 small-talk, 6 teach turns (3 duplicate-save, 3 CONFLICT), 8 ambiguous asks, 8
   unanswered asks (MISSING_FACT/BROKEN_CHAIN), 4 unconfirmed asks, 4 stray confirms, 6
   corrections, and a decoy chain (mother→father) confirmed only 8 times. Corrections are
   inserted only at unit boundaries so no legitimate pair is ever split.

2. **Miner (five rules + one frequency rule; constants, not learned).**
   - STATUS: only an ask whose notebook status is OK can start a pair.
   - PAIR: the answer is the value of an **immediately adjacent** `confirm` turn with the
     same pair_id; anything in between breaks the pair (FALL-THROUGH).
   - SUPERSEDE: a later `correct` turn replaces the standing answer for that (start, chain).
   - ANSWER-IN-VOCAB: answers outside the relation vocabulary are dropped, not guessed.
   - Frequency rule: a chain qualifies as a candidate iff length ≥ 2 and standing confirmed
     episodes ≥ 20. Candidates are visited in sorted order; a chain with no matching word
     slot is **refused**, never forced. Standing wrong = latest confirmed answer ≠ the
     ground-truth fact after replay.

3. **Sleeper (protocol-compatible `sleep(experience, notebook) -> {accepted, ...}`).**
   For each candidate it imports Experiment 46's recipe unchanged (`import
   fable_hardgate46` activates: robust loss ε=0.10, router hardened to argmax ±30 after
   every fold fit and the refit, 4-fold gate OOF ≥ 0.80 / agreement ≥ 0.90 / base unchanged
   / weights-only reload identical, 60-start audit on `rec["path"]`). Each night trains
   from the **frozen original base_state** (exactly Exp 46); the live state accumulates
   installed words for audit only. Sleep appends exactly one `sleep-derived` report row to
   the notebook — history is never rewritten.

## Registered structure

Seeds 5201/5202/5203 × wrong levels {0, 2, 4} × 3 word chains = 27 install cells, 9 logs
(3 nights per seed, notebook shared per seed). ≤ 2-wrong cells: 18. Marks (PASSMARKS.md,
sealed with the script and imported recipes before the wave): M1 zero wrong installs of 27;
M2 ≥ 15/18 at ≤ 2 wrong (brief's 12/15 scaled to 80% of 18 — mapping documented); M3 taught
facts + prefix + chain 100% over 9 sleeps; M4 each sleep < 600 s; M5 miner exact 9/9;
M6 old skills bit-identical 9/9. Wrong install keeps Exp 46's definition: installed AND
(audit disagreement > 0 OR fresh accuracy < 0.99).

## Results (see RESULTS.md for integers)

All 6 marks pass: 27/27 installed, **0 wrong installs**; 18/18 at ≤ 2 wrong (also 9/9 at
4 wrong); miner exact 9/9 (3 candidates × 20 standing, decoy refused at 8, 6 supersessions,
68 standing, standing-wrong == level each night); taught facts / prefix / chain / reload
100% over 9 sleeps; old skills and 900-question base probe unchanged 9/9; slowest sleep
7.3 s. Predictions P214–P218 (ledger, written first) all resolved TRUE.

## What is not proven

The miner's five rules and threshold, the Exp 46 recipe constants, the word slots, the 0.9
answer threshold, and the generator's noise counts are all **given by hand**. Only one log
family is exercised (200 turns, three chains, declared noise types). Multi-word installs
share a night's base but each cell still trains from the frozen wake snapshot.

## Failure protocol

Any missed mark would be recorded FAIL first; then at most one clearly described change as
v2 with its own seal, same seeds plus fresh ones. Not needed — no mark missed.
