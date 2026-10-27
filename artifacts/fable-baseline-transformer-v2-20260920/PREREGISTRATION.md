# Baseline v2 — initialization × supporting-line hint, with a lookup-fit gate

**Registered from** `design/v3/18-baseline-v2-preregistration-draft.md` (the design owner's
spec), motivated by `design/v3/18-audit-before-fable-continues.md` section 1.
**Track A validation only. 20 September 2026.**

Status: registration. Nothing in it has been run. It is **additive**: no v1 source, test,
registration, hash, checkpoint or artifact is edited, and the frozen v1 arm A-ev is
untouched and continues separately.

---

## 1. Question

Is the baseline's failure to learn attribute lookup affected by the **initialization
mismatch**, by **supporting-line supervision**, or by their **interaction**?

A model that cannot fit ordinary lookup cannot yet adjudicate length composition. So the
prerequisite below is a gate, not a footnote.

## 2. What the audit established, and what it did not

- No execution fault was found in the checked v1 paths (mask, cache/row batching, loss
  positions, END and greedy scoring, learning-rate schedule, weight decay).
- **Shown:** the baseline leaves every `nn.Linear` weight at normal **std 0.02**, while the
  successful lookup operator takes *the same draws* and calls
  `premonition_token_initialization_probe.rescale`, which multiplies each Linear weight by
  `1/(sqrt(3*fan_in)*0.02)` — i.e. rescales them to **std `1/sqrt(3*fan_in)`** (≈0.083 at
  fan-in 48, ≈4×). **Not shown:** that this caused the failure. That is what this
  experiment tests.
- **Shown:** aggregate token accuracy is dominated by END and intermediate people; ~2/3
  token accuracy coexisted with ~1/10 one-hop answers. v2 therefore reports per-role
  metrics and treats aggregate token accuracy as secondary.
- **Shown:** output-position embedding rows ≥3 receive zero loss gradient under training
  lengths 1–3. That is a length-generalization handicap, and the draft assigns it to a
  **separate later diagnostic** — see §10.

## 3. Fixed comparison

Same 69-token vocabulary, END = 68, `line` mask and positional package, causal row
encoding, width 48, 3 layers, 4 heads, MLP hidden 208, tied embeddings, loss masking and
greedy scorer as v1. **No change** to query format, embedding decay, positions, depth or
curriculum in this experiment.

| Arm | Linear initialization | Supporting-line loss |
| --- | --- | --- |
| I0-H0 | normal std 0.02 | 0 |
| I0-H1 | normal std 0.02 | 0.5 |
| I1-H0 | same draws rescaled to std 1/sqrt(3·fan_in) | 0 |
| **I1-H1** — **primary fairness control, nominated now** | same draws rescaled to std 1/sqrt(3·fan_in) | 0.5 |

**Rescaling.** Only `nn.Linear` **weights**, exactly as the operator: `RESCALE` in
`scripts/fable_baseline_transformer_v2.py` **is the operator's own function object**
(`astra_canonical_operator` already imports `premonition_token_initialization_probe as I`
and builds every canonical operator as `torch.manual_seed(seed); model = …;
I.rescale(model)`), so this is not a port. Embeddings and biases are **not** rescaled (all
biases are zero, so rescaling them would be a no-op in any case). v2 applies it in the same
order — seed, construct, rescale — so the two init arms of one seed share their random
**draws** exactly and differ only by the scalar multiply. Checked in
`tests/test_fable_baseline_transformer_v2.py`: bitwise equality of `draw × factor`, sign
preservation, and "only Linear weights move".

**Supporting-line loss.** The already-checked v1 `--evidence-aux` term at coefficient 0.5:
the last layer's head-mean attention from each result-predicting position is pushed onto
the tokens of the gold supporting row, END excluded. This matches the *availability* of
line labels, **not** the operator's internal allocation of evidence loss across three
reads. That difference is a stated limitation, not a defect.

## 4. Seeds, stream and pairing

- Seeds **1200, 1201, 1202**, paired across all four arms.
- World RNG namespace **`astra-baseline-v2-fit:seed`**. Model RNG is `torch.manual_seed(seed)`;
  the two RNGs are independent.
- The same worlds, questions, targets and ordering are identical across the four arms. The
  hint flag changes only whether supporting-row indices are attached; it consumes no RNG.
  Tested.
- Each run records `initial_weight_fingerprint`, `torch_rng_after_init_sha256`,
  `data_rng_initial_state_sha256`, `final_weight_fingerprint`, the checkpoint SHA-256 and
  the SHA-256 of `fable_baseline_transformer_v2.py`, `fable_baseline_transformer.py` and
  `fable_dispatcher_v3.py`.

**A-ev is NOT reused as a v2 cell.** The draft permits historical runs as context only
"unless their complete recipe/stream matches". The registered v1 arm A-ev uses seeds 0/1/2
and the `fable-baseline-train` namespace, so its stream does not match `astra-baseline-v2-fit`.
All four cells are therefore run fresh, at 3 seeds each: **12 runs, 4 waves**. A-ev remains
a separate registered experiment and is reported as context, never as the I0-H1 cell.

## 5. Budget and optimizer

6,000 updates; 16 worlds × 4 questions per update; six people; requested hop length uniform
over {1, 2, 3}; relation 10 excluded as a terminal at lengths ≥ 2. AdamW lr 1e-3, warmup
100, linear decay over the final third to 1e-4, betas (0.9, 0.99), eps 1e-8, weight decay
0.1 on all parameters, gradient clip 1.0. Final checkpoint only; no checkpoint selection;
no resume.

Timing is **projected, not idle-measured** (the Mac was running six registered workers):
measured 6.4–6.6 updates/s per process with 7–8 concurrent processes, and 6.61–6.67
updates/s per process in the v1 3-seed 11k wave. 6,000 updates ≈ **15–16 min** per seed;
three seeds run in parallel, plus ≈ 30 s of fit scoring per seed, so a wave is ≈ **16 min**,
inside the 25-minute ceiling and inside the draft's 1,200 s resumable-chunk rule, so no
resume machinery is registered. `--time-cap` therefore defaults to exactly that 1,200 s
chunk ceiling, which leaves ≈30% headroom over the projected 923 s. If a process hits the
cap the run is written as `incomplete.json` and reported as **"under-trained —
inconclusive"**, never as an architecture failure, and the remedy is a registered
resumable-chunk amendment, not a silent extension. A throwaway idle forward/backward
measurement must still be taken before launch and recorded.

Every run records matmul-only FLOPs (v1's convention, padded positions charged), padded and
real story tokens per update, and wall time; the fit report records greedy inference FLOPs.
**No claim of equal total System S compute is made here** — dispatcher costs are not counted.

## 6. Validation panels

Built **before any training**, by `fable_baseline_transformer_v2.py panels`, under the
shared protocol of `design/v3/18-validation-and-operator-swap-v2-preregistration-draft.md`.

- **Development-fit panel**, namespace `astra-baseline-v2-fit-panel-20260920`, 512
  independently drawn questions per cell, six-person full stories:

  | cell | hops | terminal relation | threshold |
  | --- | --- | --- | --- |
  | `fit-k1-prac` | 1 | practised (8/9, exactly 256 each) | 487/512 |
  | `fit-k1-held` | 1 | held-out 10 | 487/512 |
  | `fit-k2-prac` | 2 | practised | 461/512 |
  | `fit-k3-prac` | 3 | practised | 461/512 |

- **Untouched confirmation panel**, namespace `astra-baseline-v2-confirm-panel-20260920`,
  same four cell definitions, disjoint worlds, generated at the same time and **not read**
  until a configuration has cleared the development-fit gate. `fit --confirmation` is
  required to score it and is refused otherwise.
- RNG derivation is `(namespace, cell, unit index, attempt index)`, replayable; the attempt
  sequence is fixed at 0…255. The only rejection reasons are: no pairwise-distinct asker, a
  signature in the frozen exclusion union, a duplicate semantic signature, a duplicate
  tensor signature. **No rejection depends on any model, correctness, attention, margin or
  confidence.** Every rejection count is logged in the manifest.
- Every unit is audited with V3's independent evaluator-only interpreter; multi-hop chains
  are pairwise distinct; relation 10 is never a multi-hop terminal.
- **Exclusions.** Training receives the frozen union of (a) the v3 panels'
  `forbidden-semantics.json`, (b) the development-fit panel's signatures and (c) the
  confirmation panel's signatures, before the first update. Its file list, per-file SHA-256
  and a union hash are recorded. A training draw that collides **invalidates the run** — it
  is never silently skipped, so the frozen RNG stream cannot shift.
- **Not in scope here:** the 25-cell fresh dispatcher/baseline suite
  (`astra-confirm-dispatch-v2-20260920`) that the validation draft governs. Untouched
  **length-generalization** confirmation runs against that suite, under that draft, after
  fit qualifies.

## 7. Reported metrics

Every 100 updates, the training log records, as raw (hits, total) counts **and** ratios:

- `end_accuracy` — END tokens
- `intermediate_accuracy` — intermediate people
- `terminal_accuracy` — terminal answers
- `one_hop_terminal_accuracy` and `multi_hop_terminal_accuracy`
- `sequence_accuracy` (exact) and `one_hop_sequence_accuracy`
- `token_accuracy` — **aggregate, secondary**
- loss, the supporting-line term, **gradient norm**, learning rate, seconds, FLOPs

The same per-role decomposition is reported on the fit panel, teacher-forced, at the final
update only. `tests/test_fable_baseline_transformer_v2.py` contains a check in which END
and every intermediate person are correct and every terminal answer is wrong: aggregate
token accuracy stays high while terminal and one-hop-answer accuracy are exactly 0. That
is the v1 reporting artefact, and it can no longer hide.

## 8. Gates

Evaluated on the fixed development-fit panel at the **final update only**. Greedy decoding.
No checkpoint selection. Reported **per seed and per arm**; no averaging rescues a failure;
no seed substitution.

- **`one_hop_lookup_gate`** — `fit-k1-prac` and `fit-k1-held` each reach **487/512 on
  answers AND 487/512 on exact greedy sequences**. This is the audit's requirement that
  ordinary lookup must succeed. `composition_claims_licensed` mirrors it: **until a seed
  clears it, none of that seed's failures may be used to argue anything about length
  composition.**
- **`fit_gate`** — the above, plus `fit-k2-prac` and `fit-k3-prac` each at **461/512 on
  answers AND on exact sequences**.
- Per-token teacher-forced metrics and the equal-relation one-hop strata (relations 8, 9
  separately in `fit-k1-prac`; relation 10 in `fit-k1-held`) are reported alongside.

Failure means **"lookup/sequence fit prerequisite failed under this recipe"**, not "more
training would necessarily fix it".

Only a fit-qualified configuration proceeds to untouched length-generalization
confirmation. **I1-H1 is nominated as primary now.** The other three arms are causal
controls and exploratory for generalization. If I1-H1 fails fit, the comparison claim
stops and the next diagnostic is registered separately; a different passing arm is **not**
silently nominated.

## 9. Interpretation rules, fixed in advance

- Initialization contrasts: I1-H0 vs I0-H0, and I1-H1 vs I0-H1. Hint contrasts hold
  initialization fixed.
- All four failing leaves the startup cause **unresolved**.
- Better fit with rescaling implicates **this initialization intervention**, not every
  proposed gradient explanation.
- A hinted baseline failure still does **not** isolate decomposition from depth,
  computation, masking or position design.
- Nothing here licenses a claim about equal System S compute, about a "label-free" system,
  or about population reliability from three seeds.

## 10. Deliberately not implemented

The draft places these **after** fit succeeds, as separately registered work, so nothing
about them is implemented, varied or measured here:

- Fixed sinusoidal / shared within-row, question and output **position functions** in place
  of learned per-output-index embeddings, with the parameter-count difference stated. v2
  exposes no new position knob beyond v1's `--positions {line,absolute,none}` and runs
  `line` throughout.
- Any remedy for the zero-gradient output-position rows ≥3.
- The 25-cell fresh confirmation suite and the frozen-operator swap (validation draft).

## 11. Tiny-batch overfit check

`fable_baseline_transformer_v2.py overfit` trains a **fixed** batch (default 8 worlds × 4
questions) at constant lr until exact sequence accuracy is 1.0 or 1,500 updates, once per
init, in one process, and reports whether each init memorises it and after how many
updates. Development namespace `astra-baseline-v2-overfit`; seeds below 990100 are refused.

The draft registers it **conditionally**: "If even I1-H1 cannot fit one hop, register a
finite small-story, one-hop overfit check … before launching more long runs." It is
therefore an implementation check, not a cell of the 2×2. It distinguishes a remaining
expressivity/optimization difficulty from an evaluation bug; **it certifies nothing about
generalization**. It was built but **not run** during this build (six registered workers
were active).

## 12. Preflight requirements

Discharged by `tests/test_fable_baseline_transformer_v2.py` (75 checks) together with the
frozen v1 suites `tests/test_fable_baseline_transformer.py` and
`tests/test_fable_baseline_evidence_aux.py`, which are **imported and re-run, never edited**:

| requirement | where |
| --- | --- |
| cache/dense logits AND gradients | v1 suite (dense reference, 1e-5) |
| causal no-future leakage | v1 suite |
| loss-target shift | v1 suite, plus v2's role grid check that the terminal target IS the answer |
| mixed question-length decoding, END cap | v1 suite |
| row-permutation invariance | v1 suite |
| evidence targeting | `tests/test_fable_baseline_evidence_aux.py` (28 checks) |
| fixed paired batches | v2: the four arms draw identical worlds/questions/targets/order |
| rescaling exactly as specified | v2: operator's own function object; draw × factor bitwise; signs preserved; only Linear weights move |
| v1 parity | v2: bitwise-identical loss tensor at hint 0 and 0.5, and every parameter bitwise identical after 5 updates |
| no training/panel signature overlap | v2: frozen union, collision invalidates the run |
| fresh-run outputs | v2: every command refuses to write into an existing directory |
| dependency and checkpoint hashes | v2: `FREEZE.sha256` + per-run source/checkpoint SHA-256 |

## 13. Launch procedure

Run only when the Mac's registered waves are idle. `run_wave_v2.sh` verifies
`FREEZE.sha256`, verifies both panel manifests, refuses to start if any
`python3.12 -B` process is already running, and launches **one arm × three seeds = three
processes** per call.

```
# once, before the first wave (panels are frozen BEFORE any training)
scripts/fable_baseline_transformer_v2.py panels --kind fit \
    --out artifacts/fable-baseline-transformer-v2-20260920/fit-panels \
    --exclude artifacts/fable-dispatcher-v3-20260920/panels
scripts/fable_baseline_transformer_v2.py panels --kind confirm \
    --out artifacts/fable-baseline-transformer-v2-20260920/confirm-panels \
    --exclude artifacts/fable-dispatcher-v3-20260920/panels \
    --exclude artifacts/fable-baseline-transformer-v2-20260920/fit-panels
# then append the four panel files to FREEZE.sha256 (see the script header), then:
artifacts/fable-baseline-transformer-v2-20260920/run_wave_v2.sh I1-H1   # primary first
artifacts/fable-baseline-transformer-v2-20260920/run_wave_v2.sh I0-H1
artifacts/fable-baseline-transformer-v2-20260920/run_wave_v2.sh I1-H0
artifacts/fable-baseline-transformer-v2-20260920/run_wave_v2.sh I0-H0
```

## 14. Judgment calls where the spec was silent

Each was resolved conservatively and is listed so it can be overruled before launch.

1. **One-hop-answer training metric.** The draft names intermediate people, terminal
   answers and END. The audit's table also breaks out one-hop answers, so
   `one_hop_terminal_accuracy` / `multi_hop_terminal_accuracy` / `one_hop_sequence_accuracy`
   are added. Additive reporting only.
2. **"Equal-relation one-hop diagnostic strata"** is read as: the practised one-hop cell
   contains exactly 256 of relation 8 and 256 of relation 9, and one-hop results are
   reported per terminal relation.
3. **Which confirmation panel.** The draft asks for a confirmation panel here but assigns
   the 25-cell length-generalization suite to the validation draft. Resolved by generating
   a disjoint confirmation copy of the **four fit cells** now (sealed behind
   `--confirmation`), and leaving the 25-cell suite to its own registration.
4. **What a wave scores.** The wave trains and evaluates the fit gate only. It does **not**
   score the v3 length panels, because the draft admits only fit-qualified configurations to
   confirmation.
5. **Both answers and exact sequences** are required at each cell's threshold; the draft's
   wording is read conjunctively.
6. **`--train-namespace`** exists so v1 parity can be demonstrated on v1's stream. The
   registered arms use the draft's `astra-baseline-v2-fit` and the runner records which was
   used.
7. **`incomplete.json`** (not `failure.json`) is written when the time cap is hit, to keep
   "incomplete" typographically distinct from "failed", per the draft.
8. **Overfit defaults** — 8 worlds × 4 questions, constant lr 1e-3, 1,500-update ceiling,
   hop mixture {1,2,3} as in training. The draft says "finite small-story, one-hop"; the
   mixture is kept identical to the training distribution so the check tests the same
   targets, and the per-role report separates one-hop from multi-hop within it.
9. **Concurrency guard.** The wave refuses to start when any `python3.12 -B` process is
   running (override `ALLOW_BUSY=1`). The draft requires idleness; the audit flagged the
   factorial launcher for having no such guard.

## 15. Unverified at registration time

- Wave timing is **projected** from loaded-machine measurements and the v1 11k wave, not
  from an idle throwaway forward/backward check. Take that measurement before launch.
- The `--evidence-aux` term's overhead measured as ~0 at 30 updates under load; the
  full-length hint arms have not been timed.
- The fit-panel greedy scoring cost (≈24 s per seed) was extrapolated from a 64-unit build
  with an untrained model, which never emits END and therefore always decodes the full
  12 steps — an upper bound.
- No registered experiment, registered seed, panel build or overfit run was executed during
  this build.

## Fable's predictions

Written 2026-09-20 by Fable before freeze; no v2 run, panel build or overfit check exists yet. Known: v1 (default init, no hint) was at chance after 11,000 updates in
3/3 seeds; v1 A-ev (default init, hint) is running and unread. Start-up factorial arms A/D (the lookup operator, not this baseline): small stories start 3/3, full
stories 0/3 in 2,500 updates. My record: 3 hits / 9 misses. "Clears the gate" = the registered development-fit gate of §8, per seed (1200/1201/1202).

| id | forecast | p | falsified by |
|---|---|---|---|
| P26 | I1-H1 (operator-rescaled init + hint) clears the gate in ≥ 2/3 seeds | 0.55 | ≤ 1 seed |
| P27 | I0-H1 (default init + hint) clears in ≥ 2/3 | 0.40 | ≤ 1 seed |
| P28 | I1-H0 (rescaled init, no hint) clears in ≥ 2/3 | 0.25 | ≥ 2 seeds |
| P29 | I0-H0 clears in ≥ 1/3 | 0.10 | any seed clears |
| P30 | the tiny-batch overfit check reaches sequence accuracy 1.0 within 1,500 updates for BOTH inits | 0.75 | either init fails to memorise |

If P30 fails for an init, that arm's failures are an optimisation/implementation problem and say nothing about composition.
