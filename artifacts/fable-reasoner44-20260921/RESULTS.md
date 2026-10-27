# Experiment 44 — results (2026-09-21): the reasoner as callable skills + router over a notebook

Registered seeds **4102 / 4103 / 4104**, one wave, no repeats, no retuning, no v2 needed.
Marks were written and hashed (`SEAL.sha256.txt`, sealed 2026-09-21T23:06:27Z) before any
registered run. Development used throwaway seed 9999 only.

Trainable numbers: **64** for the whole base reasoner (an 8x8 token→skill logit table) and
**27** per new word (3 stages x 9 options). Wall-clock per seed: base 14.2–14.5 s,
sleep at 20 episodes (including both controls, all three words) 20.7–21.3 s,
sleep at 50 episodes 10.3–10.4 s. Whole wave, three seeds in parallel: **51 s**.

## Marks

| Mark | 4102 | 4103 | 4104 |
|---|---|---|---|
| **R1** fit, 1–3 hop, fresh N=60 (need ≥ 0.99) | PASS 1.000 | PASS 1.000 | PASS 1.000 |
| **R2** depth 4 / 6 / 8 / 10, fresh N=60 (need ≥ 0.95 each) | PASS 1.000 / 1.000 / 1.000 / 1.000 | PASS 1.000 / 1.000 / 1.000 / 1.000 | PASS 1.000 / 1.000 / 1.000 / 1.000 |
| **R3** same on N=200, all-new names | PASS 1.000 (1–3) and 1.000 at every depth | PASS 1.000 / 1.000 | PASS 1.000 / 1.000 |
| **R4** honesty, 400 missing-fact chains (need unknown ≥ 0.99 and 0 confident wrong) | PASS 1.000, 0 wrong | PASS 1.000, 0 wrong | PASS 1.000, 0 wrong |
| **R5** sleep, 3 words x {20, 50} episodes (installed AND ≥ 0.95 fresh) | PASS 6/6, all 1.000 | PASS 6/6, all 1.000 | PASS 6/6, all 1.000 |
| **R6** slept word inside a 2–4 token chain (need ≥ 0.95) | PASS 1.000 (N=200: 1.000) | PASS 1.000 (1.000) | PASS 1.000 (1.000) |
| **R7** base unchanged / reload identical / random episodes rejected | PASS | PASS | PASS |

All 21 seed-marks PASS. No mark was missed, so no v2 change was made.

Routing the base reasoner found: the identity permutation (token *r* → skill *r*) in all three
seeds, with the smallest winning weight 0.99990 / 0.99992 / 0.99990.
Routing each word found (all three seeds agree on the chain, the "keep" slot lands wherever it
is not needed): `maternal_grandmother` = mother→mother, `boss_of_spouse` = spouse→boss,
`doctor_of_mothers_friend` = mother→best_friend→doctor. The cross-validation always chose the
largest checkpoint (800 updates).

## Recorded, not gated

- **10% wrong episodes (2 of 20): NOT installed, 9/9 word-seed runs.** Best cross-validated exact
  match across all checkpoints was 0.00–0.20, nowhere near the 0.80 floor and far below the 0.90
  you would naively expect from "18 of 20 are right". See the surprise below.
- **100% random episodes: NOT installed, 9/9 word-seed runs**, best CV match 0.00 everywhere.
- **Depth stress** (measurement only, written after the seal, `scripts/fable_reasoner44_stress.py`,
  `stress.json`; 100 resolvable chains per depth on the N=200 village, no retraining): exact
  accuracy **1.000 at 12, 16, 20, 24 and 32 hops in all three seeds**. The probability left on the
  correct person decays slowly and linearly: min 0.99900 at 12 hops, 0.99749 at 32 hops
  (about 9e-5 lost per hop). Extrapolating that straight line, the 0.9 answer threshold would not
  be reached until roughly a thousand hops. **This extrapolation was not run.**
- Episode supply: an N=60 village cannot provide 50 *distinct* people whose 2- or 3-relation
  composite resolves. Distinct people behind the "50 episodes" condition were 29–50 depending on
  seed and word; the rest are repeats. Folds are split **by person**, so repeats cannot leak
  across the cross-validation split, but "50 episodes" is honestly "up to 50 episodes over 29–50
  distinct people".

## The surprise / the one thing worth remembering

Two wrong answers out of twenty do not give a slightly-wrong word — they give **no word at all**.
A soft mixture over skills cannot satisfy two contradictory targets, so instead of fitting 18 and
missing 2, it spreads probability everywhere and falls under the 0.9 answer threshold on
*held-out episodes it would otherwise have got right*. Cross-validated exact match collapses to
0.00–0.20 and the gate refuses to install. That is **safe** (a 10%-noisy teacher cannot install a
half-right rule) but it is also **brittle** (a 10%-noisy teacher cannot teach at all). Nothing in
the design lets it learn the majority chain and shrug off the outliers.

No bug was found in the runs. One thing to flag about the code rather than the science: the
scoring helper (`fable_reasoner44_score.py`) and the stress probe were written *after* the seal
and only read run outputs; they are reporting tools, not part of the registered experiment.

## What this means

- The whole depth story falls out of the design: because a token's routing does not depend on
  where in the chain it sits or on how long the chain is, **there is no length parameter anywhere
  in the model**. Training on 1–3 hops and running 32 is not generalisation in the usual sense; it
  is the same 64 numbers applied more times. That is the direct answer to the length wall that
  killed experiments 43A/43B/43C.
- Facts stayed entirely in the notebook. The learned weights index relations, never people, and
  the lookup matrices are rebuilt from the notebook at run time. Swapping in a 200-person village
  of unseen names is a data change, not a model change.
- Sleep taught three genuinely new relation words from 20 raw (person, word, answer) episodes, by
  gradient descent on 27 numbers, with nothing proposing or writing a rule, and the new words then
  worked as ordinary tokens inside longer questions.
- The install gate did its job on both control conditions.

## What this does NOT mean

- **R3 is nearly free by construction, not an empirical finding.** No person identity can enter
  64 relation-indexed weights, so a new village with new names *cannot* affect them. R3 tests that
  the implementation honours the design; it is not evidence about generalisation in a model that
  does store entities.
- **R4 honesty is given, not learned.** The UNKNOWN sink absorbs and the 0.9 threshold is
  hard-coded. Any chain touching a missing fact loses its mass to the sink arithmetically. The
  model is not deciding to abstain; the wiring cannot do anything else.
- **R1/R2 are a very easy learning problem.** 64 parameters, and the target is the identity
  permutation. That all three seeds found it is reassuring wiring evidence, not a hard result.
- **No baseline was run.** There is no plain transformer, no retrieval system, no comparison of
  any kind in this experiment. Nothing here supports a claim that this beats anything.
- **No language anywhere.** Questions are token sequences, not English; names are opaque IDs; the
  notebook is a dict, not the exp-41 notebook contract. This is not connected to the talker.
- **Relations are uniformly random partial functions**, mutually unconstrained. There is no
  consistency (a person's "mother" may be their own "boss"), so nothing here tests reasoning over
  a structured or contradictory world, and composites are exact chains by construction.
- **Only exact chains were taught.** Every new word is exactly a 2- or 3-relation chain of skills
  the system already had. No word requiring a skill it does not have, no disjunction, no
  condition, no word that is only approximately a chain.
- Noise tolerance is unmeasured beyond the single 2-of-20 point, which failed to install.

## Given by hand (not learned)

1. The hop loop: exactly one routed skill call per token, in order.
2. The halt rule: stop when the token tape is empty. Nothing counts hops, nothing learns to stop.
3. The lookup matrices, built at run time from the notebook, including the UNKNOWN sink and the
   fact that it absorbs.
4. The 0.9 answer threshold and "otherwise say unknown".
5. Every new word is exactly 3 routing stages, one option of which is "keep" (do nothing).
6. Which three composites are taught, and that episodes are drawn only from people for whom the
   composite resolves (a teacher states facts they know).
7. R = 8 relations, and the 1–3 token training range.
8. The gate's own constants: 4 folds, the 0.80 cross-validated floor, the 0.90 refit agreement
   floor, the checkpoint list.

What is **learned**, and only from final answers: which skill each relation token calls (64
numbers, base), and which 3-stage chain of skills each new word calls (27 numbers per word,
sleep). No hop, no intermediate person, and no skill choice was ever supervised.

## Reproduce

```bash
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
shasum -a 256 -c <(head -3 artifacts/fable-reasoner44-20260921/SEAL.sha256.txt)   # check the seal
bash artifacts/fable-reasoner44-20260921/wave.sh                                   # whole wave, ~51 s

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/fable_reasoner44_score.py artifacts/fable-reasoner44-20260921/runs      # the marks table
(cd scripts && PYTHONPATH=. $PY fable_reasoner44_stress.py ../artifacts/fable-reasoner44-20260921/runs)
```

A single stage on its own:

```bash
$PY scripts/fable_reasoner44.py --stage base  --seed 4102 --out artifacts/fable-reasoner44-20260921/runs
$PY scripts/fable_reasoner44.py --stage sleep --seed 4102 --episodes 20 --out artifacts/fable-reasoner44-20260921/runs
$PY scripts/fable_reasoner44.py --stage base  --seed 9999 --out /tmp/smoke --smoke   # smoke, no claim
```

## Files

- `scripts/fable_reasoner44.py` — the whole experiment (world, notebook, skills, router, sleep, gate).
- `scripts/fable_reasoner44_score.py`, `scripts/fable_reasoner44_stress.py` — post-seal reporting only.
- `artifacts/fable-reasoner44-20260921/` — `PASSMARKS.md`, `SEAL.sha256.txt`, `wave.sh`,
  `runs/` (3 base + 6 sleep JSONs, checkpoints), `logs/`, `scores.json`, `stress.json`,
  this `RESULTS.md`, `RESULTS-SEAL.sha256.txt`.
