# creative/: code for C1 and C2 (creative roadmap, 2026-10-06)

Spec: `creative-roadmap-2026-10-06.md` sections 6 (C1) and 7 (C2). Imports `custom_io` (B2) and edits nothing there.
**Nothing here trains B2.** CPU smoke tests only. Both tests wait for B2's 6-seed confirm (seeds 200-205 = the 6 parents).

Run the tests (no data needed, tiny random B2): `python3 -m creative.tests.test_c1` and `python3 -m creative.tests.test_c2`.
Branch note: this branch is cut from `claude/custom-reader-talker-4x309r` so `custom_io` exists; the diff of this PR is `creative/` only.

| File | What it is |
|---|---|
| `programs.py` | B2's slots as python ints: `Try`, exact run, answer cone, canonical program key, forced-replay training form (`train_form`, `register_targets` seeds `progparse._CACHE` so `Ledger.gold()` forces the logged slot ids) |
| `puzzles.py` | C1 puzzle generator, exact solver (all solutions), twin targets, hash-sealed splits (`data/c1/`), S0 floors |
| `checkers.py` | the two independent checkers + B2-executor replay -> `accept / reject / unresolved` |
| `sampler.py` | the shared sampler: heads sampled at a temperature, top-8 first-step branching, duplicates dropped; also `loops:K` |
| `scoreboard.py` | luck, reach@4/@32, first try, variety, STOP-rule luck, own-vs-twin aim, DEV gates, temperature choice, lesions |
| `arms.py` | C1 arms W, R, H, H', PC (N = no records) |
| `sleep.py` | resume from checkpoint, fresh-AdamW sleep with forced targets + skills replay, <= 4 visits per record |
| `fewshot.py` | C2a checker over input roles, C2b arms W/R/H, comparison-net data sets, synthetic rule kinds (smoke only) |
| `cli.py` | `build-splits`, `floors`, `dev-gate`, `lesions` |

## What is built, against the spec
- **Puzzles (C1).** 3 numbers from 3..40 minus 10, T >= 1, T not a constant or a given number, exact division, solvable, no 2-number shortcut. Splits by number set: practice 1,024 / DEV 128 / T1 256 / T1b 256 / X 128 four-number. Twin target on every DEV/T1/T1b puzzle. One fixed instruction line, no digits in it. Sealed: `data/c1/MANIFEST.json` holds each file's sha256 and `load_split` refuses a file that does not match.
- **Checkers.** `rules_a` (recursion, leaf multiset) and `rules_b` (reverse reachability + consumption pool, Fractions) written differently; 23 planted bad programs of every kind are rejected by both, with and without the value check; 10,000 random and structured tries never split them; B2's own torch executor replays every accepted try. Unresolved (disagree, replay mismatch, crash) = no hit.
- **Shared sampler (D4).** Same code for C1 and C2. Tested: its greedy mode equals `Ledger.run` (program, answer pointer, values), seeds repeat exactly, branches really force their first step, the answer key can be blanked without changing a single try.
- **DEV gates.** Cold start (accepted try within 32 on >= 10% of puzzles), sameness (>= 4 distinct result-changing programs per puzzle). `cli dev-gate` picks the temperature on DEV first.
- **Sleep plumbing.** Resume from a checkpoint (weights only: checkpoints hold no optimizer, so every sleep is a fresh AdamW, as the spec says), half puzzle rows / half replay, visit cap enforced, record ids must be unique. A tiny model overfits the forced targets (loss 20.1 -> 1.8 in 120 updates).
- **C2a without changing B2.** A try is a program over the query's input slot, the constants and its own results. To re-run it on example i the query slot is re-bound to x_i. Pointers at other prompt numbers are rejected, and the program must read x. Two executions (python ints, B2's torch executor over the examples as one batch). `mechanism_report` gives the "agrees with the key on >= 99% of accepted tries" mark. So the input-role pointers the roadmap listed as a need from B2's owner are not needed for the check; the model still has to learn to point at the query slot.
- **C2b arms.** W (tries fitting every example, <= 2 distinct per question), R (run on every example, fit none-or-not-all, matched count, separate pool), H (R's tries with the example outputs rewritten to what the try computes; every relabel fits). Records are answered by the try's own output; the key is never read (tested by corrupting every key).

## Not built yet (waits)
- The warm-up on 2-number puzzles and the DEV choice of lr / update count with the PC arm (needs a B2 parent and a GPU or a slow CPU).
- The power simulation and the spread between parents (needs real DEV numbers).
- The orchestration that runs 36 sleeps and scores T1 / T1b (a small script once B2's confirm is in; it is just these functions in a loop).
- Real C2 rows: the skills data's fewshot_number_rule / rule_apply are parsed by `fewshot.parse`, but that data is not in this repo's checkout, so only synthetic kinds were smoke-tested. Sealing the held-out rule kinds by hash is C2's own step.
- The plain-net and fresh-net training for "examples to learn" (`labelled_sets` builds the k = 0, 8, 32, 128 data only).

## Spec revision of 10-06 (relay from the roadmap thread), applied
1. **Signal gate replaces cold start** (`scoreboard.dev_gate`): >= 50% of DEV tries follow the rules AND an accepted try on >= 100 distinct practice puzzles. Reach@32 is report-only; reach@4 is the reach mark (and what `tune_temperature` picks on).
2. **Sameness gate** = distinct rule-following programs (canonical key) >= 4 per puzzle. `distinct` (result-changing) is still reported; variety is reported with and without branching (`nobranch_*`).
3. Puzzle generator unchanged. Correct-solution variety is report-only: `cli score --split x`.
4. **Aim check** (`scoreboard.aim_check`, `cli aim`): own tries, twin-prompt tries scored on the real target, and the value-blind rule follower (`sampler.rule_follower_tries`, matches the exact floor: 2.25% vs 2.39% on 64 DEV puzzles), luck and reach@4. A report, not a gate; repeat on W.
5. **F1** and the verdict names live in `marks.py` (`c1_marks`, `c1_verdict`: void -> gate stop -> placebo too close -> PASS with first answers / PASS, search only -> rules only -> gain with harm -> proved wrong -> not shown; `c2b_verdict`). Tested on synthetic parents.
6. **Lesion: donor only** (`scoreboard.lesions`: donor_ok = donor luck <= rules-only floor). loops:0 is reported.
7. **DEV-only pilot** (`creative/pilot.py`, `cli pilot`): raw parent gates + aim, shared warm-up on 2-number solver puzzles, warmed-parent gates + aim, PC-arm lr/update grid on DEV. Reads no T1/T1b/X. Without `--skills-train` there is no replay and warm-up harm on skills is not measured (flagged `no_replay`).
8. **C2:** `fewshot.find_reference` / `representability` (a kind is sealed only if every sampled question has a reference program in B2's executor within 7 steps), `value_blind_floor`, `fewshot.dev_gate` (reach@32 >= 10% AND >= 3x the floor's reach@32, sameness >= 4), `marks.c2b_verdict` (first try W-N >= +15, W-R >= +10, reach@4 and skills within 2 of N).

## Numbers from this code (CPU, no model unless stated)
- Value-blind rule follower on DEV: 2.4% per try, 9.2% pass@4, 48.8% pass@32. Only about 58% of its tries count as rule-following (inexact division and the like), so the 50% signal threshold is not far above a random rule follower; the practice-puzzle count is the real signal test.
- Mean solutions per target: practice 1.9, DEV 2.0, T1 1.9, T1b 1.7, X 4.4.
- The uniform floor is near 0 and a few thousand samples cannot resolve it.
- Forcing the top 8 first steps keeps about 7 distinct programs per puzzle even at near-zero temperature, which is why the gate now counts rule-following programs.
- `loops:0` writes no steps, so its luck is 0 by construction.
