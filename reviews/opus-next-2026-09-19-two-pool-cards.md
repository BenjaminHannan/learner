# Opus execution prompt: two-pool card writer

Written after the overnight run `ovn-20260918-235851`.

## Before you start

**Authorization.** Run this only after Astra or Ben authorizes it. It does not replace
`reviews/opus-execution-03-solvability.md`; ordering is their call.

**Constraints:**
- Local Mac only. $0 rental, no BensPC, no paid services.
- At most **30 minutes total** for the whole experiment on one ledger. That covers training, evaluations,
  probes and reruns. It is a ceiling, not a target.
- Freeze source and data before any compared run.
- `full_verdict: false`.
- Do not edit `learnlab/`, other workers' files, or any existing Premonition file. Add new files only.
  The one exception is `premonition/card_pools.py`: it was prepared overnight and never used, so defects
  found in review may be fixed there.

**Writing.** Explain results to Ben in simple language (he is a high-school student) first, with technical
evidence after.

## The question

Does giving every memory card **two separate attention pools** stop the identity-versus-value race? One pool
builds the key, which is used for finding the card; the other builds the value, which is used for reading the
answer.

The test: do evidence-supervised retrieval **and** reading both learn on every seed under D's default curriculum?

## What is known (read these first)

- `reviews/opus-overnight-2026-09-19-ovn-20260918-235851.md` §5.
- `design/research/2026-09-19-overnight-research-note.md` §3 and §4A.

**How the writer works now.**
- `CardWriter` in `premonition/model.py:171` pools a line with one softmax score (`self.pool`, `Linear(d, 1)`).
- Both key and value come from that one pooled vector.

**What went wrong tonight.**
- Trained pools put 70–98% of their mass on one or two tokens.
- Cards kept the person or the value, never both, depending on schedule and seed.
- The reader states still encode both (2304/2304).

**Baseline to reproduce.** Exp 2, arm `bypass-k1`: D-card-bypass reader, top_k 1, no teacher distractors,
max_loops 4, D's default curriculum.
- It learns retrieval but never reads: pure reading 32/512, card value 125/2048.
- The seed-1 long-read run failed the same way.

## Implementation (additive; prepared overnight, untrained)

1. **Review `premonition/card_pools.py`.** It was written by the overnight run and has not been trained.
   - `TwoPoolCardWriter` adds `pool_value` (`Linear(d, 1)`, +33 parameters at d = 32). The key is built from
     `pool` and the value from `pool_value`.
   - `MeanPoolCardWriter` uses uniform weights, with no learned pool.
   - Model classes: `D-two-pool`, `D-mean-pool`, `D-card-bypass+two-pool`, `D-card-bypass+mean-pool`. Each has
     its own `identity()`.
   - Construction keeps the same-seed baseline and the global random stream intact. `pool_value` starts as a
     copy of `pool`, so at init the two-pool model computes exactly what single-pool D computes.
   - Fix defects if the review finds any; otherwise do not rewrite it.
2. **Tests: `tests/test_premonition_card_pools.py`** (6 tests, passing overnight). They check:
   - exact equality with D at init (keys and values);
   - the random stream is kept;
   - the value pool changes values but not keys;
   - the mean pool equals the uniform line mean;
   - the full objective reaches both pools;
   - distinct identities.

   The full Premonition suite was 126 tests with 1 skipped (see the overnight journal's final check).
3. **Harness `scripts/premonition_twopool.py` (to write).**
   - Reuse `scripts/premonition_ovn_retrieval.py` by importing it; do not edit it.
   - Give it its own `OUT`, ledger (hard cap 1800 s) and a **new frozen snapshot that includes
     `card_pools.py`**.
   - Reuse the frozen ladder data: `artifacts/opus-ovn-20260918-235851/exp1/data`. Verify the manifest hashes:
     validation `3ba2f6ca…`, test `85c14090…`, train digest `7da7fc28…`.
   - Reuse the probes `card_content_probe.py` and `pool_attention_probe.py`, copied and adapted so they report
     both pools.
   - The extra 33 parameters change the measured FLOPs per step slightly, so the FLOP-budget stop may land a
     few steps differently. Report the actual steps.

## Runs (requested 1500 steps; the trainer stops at its FLOP budget, about 1405–1517 steps)

| Arm | Seeds | Purpose |
|---|---|---|
| single pool (baseline, identical code path to tonight) | 0, 1 | Reproduce the race |
| two pools | 0, 1 | The candidate |
| mean pool | 0, 1 | Simplest competitor |

- Each run takes about 225 s including its evaluation, so six runs come to about 1,350 s.
- **Only if** both two-pool seeds meet the support rule on validation: add two-pool seed 2, then single-pool
  seed 2 if the remaining ledger allows.
- Stop before any run that cannot finish under the cap.
- The no-memory reference is tonight's D-noask: 41/512 at 3750 steps. Do not rerun it.

## Measure (validation for every choice; test only for checkpoints named in the journal beforehand)

- **Pure reading:** gold cards, no fetch; 1-hop, 2-hop and held-out.
- **End-to-end own retrieval:** fixed K2/K3/K4 accuracy, plus how often the gold card was fetched.
- **Controls:** cards removed; hop recall (link and answer card) for practised and held-out 2-hop.
- **Second-fetch classification:** reuse `artifacts/opus-ovn-20260918-235851/exp2/hop2_miss.py` (right
  relation / right person).
- **Probes on each pool:** pool mass on [marker, person, relation, value, filler]; key → person and relation;
  value → value.
- **Consistency pairs** on test for the final checkpoints (relevant, tempting, link).

## Pre-registered outcomes

- **Support.** Both two-pool seeds reach all of the following:
  - pure reading ≥ 486/512;
  - end-to-end 1-hop K4 accuracy ≥ 90% of the gold-fetched count;
  - key-probe person ≥ 90%;
  - value-probe value ≥ 90%.
- **Prefer the mean pool** if it meets the same bar, because it is simpler.
- **Abandon or rethink** in any of these cases:
  - any two-pool seed fails reading or retrieval;
  - both pools concentrate on the same tokens;
  - the single-pool baseline does *not* show the race. That would mean tonight's diagnosis does not reproduce;
    report it as such.
- **Not expected to change: held-out 2-hop.**
  - Tonight the second fetch asked for the question's relation 0/171 times; it uses relations practised at
    hop 2. That needs a compositional query (research note §4B).
  - Report it anyway. Two pools may raise the right-person rate of the second fetch (144/341 when practised),
    since link cards would keep the friend.

## Rules

- Report every run, including failures and stopped runs.
- Keep test out of selection.
- Questions from one visit are clustered and not independent.
- Label synthetic-vocabulary and gold-evidence diagnostics.
- Make no claim about Think. If any claim about recurrent reasoning is made, add a trained no-Think control and
  a final-loop-only-supervision arm first.

## Deliverables

- **Report:** `reviews/opus-two-pool-<date>-<run-id>.md`. Open with what we learned, what improved, what remains
  uncertain, the best next step, and the exact training seconds and $0.
- **Run records:** journal, ledger and `SHA256SUMS` under `artifacts/opus-<run-id>/`; frozen source under
  `archive/opus-<run-id>/`.
- **Decisions log:** append to `design/research/2026-09-18-decisions-log.md`, keeping results,
  recommendations and adopted engineering changes separate.
