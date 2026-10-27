# 26 — Dispatcher fault-localisation probes: registration-ready design (Fable review)

Author: Fable reviewer subagent, 2026-09-20. NEW file; edits nothing; not under Astra's name.
Companion to `design/v3/25b-gpt6pro-answer-adjudication-fable-review.md`. Status: **design ready
to register** — the builder freezes it by recording this file's sha256 and entering forecasts
P102–P111 in `artifacts/fable-predictions-ledger.md` BEFORE the first probe invocation.
Paths are relative to the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`;
`BASE/` = `/Users/ben-hannan/Desktop/projects/beautiful-model` (read only).

## 0. In plain words (for Ben)

We have 21 saved controllers. For twelve of them (the "v4" ones) we already know, from files on
disk, *which part* makes the first mistake on long questions: not the STOP button, but the pointer
that picks the next operation (or, in the register arms, the pointer that picks the next person).
For the nine controllers from experiments 19 and 19b we only know the *shape* of the failure (too
few calls, always ending on the right attribute word), not which part would still work if the
other parts were handed to it. This probe runs those nine through the same "hand it some parts
and watch the rest" test, using the twelve v4 controllers as a known-answer check that the probe
itself works. Nothing is trained. It takes about a quarter of an hour on one Mac thread.

Why this, and not GPT-6 Pro's probe set as written: its P1 is already answered for v4; its P3 needs
worlds our generator never makes; its "one fix" (a new STOP head) is vetoed by its own rule on the
existing data (25b section 1). What is genuinely unknown is whether the 19/19b controllers —
trained with cap 8 and, for U5/U8, with longer practice and the same call cost — still have a
healthy STOP and which pointer limits them.

## 1. Question, and what is NOT being asked

Q1. In each 19/19b D checkpoint, which component makes the first free-run fault on long questions,
and which single handed component (operation / subject / STOP / operation+subject) restores strict
success?
Q2. In the learned-position checkpoints, does the operation pointer's jump to the attribute follow
the *number of calls made* or the *position it last pointed at*?
Q3. Do adjacent LINK positions, and the LINK-versus-attribute logit margin, degrade with depth?

Not asked: whether any controller "works" (no pass/fail claim about a system is made or changed);
anything about the 19b confirmation suite (not built, not touched); anything about the transformer
baseline.

## 2. Exact checkpoints (all exist, all load, hashes verified on 2026-09-20)

Frozen operator for every probe:
`BASE/artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt`
sha256 `e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec` (load with
`TR.verified_operator()`, `scripts/fable_novelty19_train.py:234`). `OracleOperator`
(`scripts/fable_dispatcher.py:543`) is run alongside only to separate operator error from
controller error.

**Family 19-awake** (reg+ctx, practice 1–3 calls, train cap 8, 6,000 updates) —
`artifacts/fable-novelty19-replay-20260920/runs/awake-D-s{seed}/ckpt-006000.pt`

| seed | sha256 |
|---|---|
| 1900 | `bd4330b6737600ab8b36564237e117244607729c8f2bc6a84c003bd33cabf4b1` |
| 1901 | `56dbc8f5e96b210eef29441d8dbaec2c79c816faa33f84ebe4167db88c58632e` |
| 1902 | `b3c182ebfdac9433ab379425f175fedfa58fdf9a2ad181d6601e2d9423fc5740` |

**Families 19b-U5 and 19b-U8** (continuations of the above, 2,000 updates, practice 1–5 or 1–8) —
`artifacts/fable-novelty19b-u8-20260920/runs/offline-D-s{seed}-{U5|U8}/ckpt-002000.pt`

| seed | U5 sha256 | U8 sha256 |
|---|---|---|
| 1900 | `3ba084db4cf17dc8680c2419f02cb11a7e22b7e9aa9e0c16c6f1a540799d9989` | `2cb2675200db919a8a0e89af40d7b5960956988229474a5017340ce8002d379a` |
| 1901 | `1034f27c871d40809ba30e20f7299f5995961538fac90fab6e5ef114dbc43e20` | `898fd21affc6624eeaf81e64555516b4a8245f233397b615080cca0d93d0674f` |
| 1902 | `9de47eafeed754e820be46e609402ae74e91eb50279db0299a8e16a1f3955045` | `d90f51b37fc42abff8510d17345b352ecafe1e6181888be3518a3051be441980` |

Load all nine with `TR.load_run_checkpoint(path, 'D')`
(`scripts/fable_novelty19_train.py:916-935`; it re-verifies the recorded sha and the weight
fingerprint and refuses on mismatch).

**Optional descriptive family 19-U** (exp-19 uniform arm; reported, not in the decision table) —
`artifacts/fable-novelty19-replay-20260920/runs/offline-D-s{seed}-U/ckpt-002000.pt`:
s1900 `4ad7fd385b6c3a9759e132e0a40a930c648dc72d5c19a62ddad1dd104db73163`,
s1901 `c4a2ad8939b4dbc7ba4a574ed8a382c81818ac795876032b9e0550af2fc854d1`,
s1902 `2d28373fa937e2aa44e0ced9d645876b1492e9a217e132d2f2259cfa4f1333e0`.

**Positive-control families v4** (train cap 4, practice 1–3) —
`artifacts/fable-dispatcher-v4-20260920/{arm}/seed-{n}/dispatcher.pt`, load with
`V4.load_checkpoint(run)` (`scripts/fable_dispatcher_v4.py:826-842`).

| arm | seed 0 | seed 1 | seed 2 |
|---|---|---|---|
| reg-ctx | `022125ac80b8fbd7702506e00d169a0dfc489463e0c5cd6a2dd0bebe9ce5a0cc` | `6dc0e9ca72303bfd08d6b1ca9141f9960c4580e4ced7d5e03406dd9669a394f2` | `aba9da4d3ad8e403b7fcfbd32ff034cd3cfb9c63b2c1fd125537e5c220c003e3` |
| ctx | `f5eb693edfc0616b1eeac01059159a254f9bd928a8ddf011278a7c547c640b56` | `42444cea7e3973ddd918a52849378a5664c380135cae4cbac4dcd36562dc7cf9` | `5f96206b67388de36bf2337aa7b2d14001f3e1047aa2febfe8541088379bdce0` |
| reg | `dec8a6363303410677469a298dd144ee49d798acdc80b1b80cbd516a86724c1a` | `b36a5d84ee01d853abd8263ce153fe3c69f0b4617dcf7e58d3281f23d73156e1` | `4282a44067d22fb66251aeabe7e9beeb7ae1942dc4e6f6c3055c38970aa8bdeb` |
| v3-repro | `a62b9be8f8c2357b59d05c8442dd294b76dc767710d88553d97b68b934552244` | `3b259b05799075bedba58d9caadb74df0fbdb9a09629a3506a30386561ca2763` | `edd13d508c60cc88b2d4adf1231c52bbf16b0a0db09e9c7c76fb0f9ba2743ff6` |

Code hashes at design time (the builder records them again at launch and stops on any change):
`scripts/fable_dispatcher_v4.py` `f4e8ffd05b25662c052d6f2d508cdd7bb30bd4ab54c188cd74fd9791d5dff4e2`;
`scripts/fable_dispatcher_v3.py` `8fa4674d1b1dbcad5ae4fe51f4bfe74fe3fb6be3361569b825a4183be3aa8d53`;
`scripts/fable_dispatcher.py` `2081a94cae4f3d152230e86d58772d4c5aeabdb03dac46be5efff85fefa91545`;
`scripts/fable_novelty19_train.py` `77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8`;
`scripts/fable_novelty19_data.py` `ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de`.

## 3. Probe panel and seeds

Fresh units from `V4.throwaway_unit(cell, index, namespace)`
(`scripts/fable_dispatcher_v4.py:534-569`), whose RNG is `random.Random(f'{namespace}:{cell}:{index}')`.

- namespace: **`fable-probe26-v1`** (new; differs from the v3 registered panels, from
  `V4.THROWAWAY_NAMESPACE`, and from experiment 19's `NS_DEV` / `NS_CONFIRM`).
- cells: `k3-prac, k3-held, k4-prac, k4-held, k5-prac, k5-held, k6-prac, k6-held, k8-prac, k8-held`
  (16-person worlds, as defined in `scripts/fable_dispatcher_v3.py:113-116`).
- indices 0–63 in every cell: 640 units. No other randomness: every rollout is greedy.
- evaluation cap 16 (`V3.EVAL_CAP`, `fable_dispatcher_v3.py:105`), the cap both scorers used.
- The probe writes its panel (tokens, truth chains) and a sha256 of it into the output folder
  before scoring anything.

Corrections to GPT-6 Pro's panel: no "seed 21000" (our generator is namespaced, not integer
seeded); no self-loop worlds (`build_world` never produces a self-friend,
`fable_dispatcher_v3.py:181`, and the operator never saw one); k = 6 added, because 19b's
interesting behaviour is at 6 calls; final relations are the cell definitions' practised (8/9) and
held-out (10), which covers its "relations 8 and 10".

## 4. The probes and what is logged

Everything goes through `V4.score_side_v4(..., policy_factory=...)`
(`fable_dispatcher_v4.py:745-779`) and `V4.rollout_v4(..., policy=..., record=[], gates=[])`
(`:385-513`). `record` stores the model's **native** subject, operation and STOP logits and the
state at every step, even when the executed action was forced (`:493-499`). STOP logits are
2-way; index 1 means stop (`:507`).

**Probe A — free run, first-fault typing.** Greedy, no policy, trained operator (and oracle
operator as a check). For each failing unit, walk the transcript against the truth chain and take
the first index j that differs (or the length mismatch). Categories, tested in this order:

1. `OPERATOR` — subject token and operation token right, returned token wrong.
2. `OP_EARLY_ATTR` — the operation token is a relation (8/9/10) where the chain has LINK.
3. `OP_RUN_ON` — the operation token is LINK where the chain has the terminal relation.
4. `SUBJECT` — operation token right, subject token wrong.
5. `STOP_EARLY` — the transcript is a correct proper prefix and the status is `answered`.
6. `STOP_LATE` — the full chain is correct and further calls follow (answered late or `over_cap`).
7. `INVALID` — status `invalid_action` after a correct prefix; sub-typed by which pointer was
   illegal, from the `pointers` record (`:455-457`).
8. `OTHER`.

Logged per cell: strict, answers, calls histogram, first-fault index histogram, category counts.
Because all LINK tokens are the same operation and strict is token-based (`:774`), picking a
different LINK position than the "gold" one is not a fault, by design.

**Probe B — handed-component replays.** The five existing kinds (`V3.INTERVENTIONS`,
`fable_dispatcher_v3.py:929-967`): none, operation, subject, STOP, operation+subject. Components
are forced only while `step < hops`; afterwards everything is the model's own. Logged per cell and
kind: strict, answers; for the operation+subject kind additionally, per step t: the category of
the native operation argmax (`REL` / a not-yet-used LINK / an already-used LINK / other), whether
the native subject argmax is the gold slot, native p(STOP), the median logit margin
(best not-yet-used LINK minus the attribute position), the register gate value where a register
exists; and the failure sub-type (`STOP_EARLY` or `STOP_LATE`).
This replaces GPT-6 Pro's P1 and the useful part of its P2.

**Probe C — offset start (replaces its P3 state transplant).** Learned-position checkpoints only
(v4 `ctx`, v4 `reg-ctx`, all 19/19b D). Cells `k8-prac` and `k8-held` (seven LINKs at question
positions left+2 … left+8, attribute at left+9). A new policy, local to the probe script, forces
the gold subject at steps 0 and 1 and forces the operation pointer to two chosen LINK positions;
from step 2 on the model is free. Conditions:

| condition | forced operation positions (steps 0, 1) | "next position" |
|---|---|---|
| S0 (as in a normal run) | left+2, left+3 | left+4 |
| S3 (start deeper) | left+5, left+6 | left+7 |
| S5 (control: the last two LINKs) | left+7, left+8 | left+9 = the attribute |

Every forced call is a legal friend-lookup, so the controller is in a state it could have reached
by its own choices; no state is patched by hand. Logged at step 2: category of the native
operation argmax — `REL`, `NEXT` (last forced position + 1), `THIRD` (left+4), other LINK, other —
and the logit margin REL minus best LINK. Reading: if S3 still gives `REL`, the rule follows the
number of calls; if it gives `NEXT` or another LINK, the rule follows the fed-back position.

**Probe D — geometry (its P4, re-aimed).** Learned-position checkpoints only. From
`model.question_context` (`:267-293`): `sep_trained` = median distance between the context vectors
of LINK #1 and LINK #2 in the k3 units; `sep_long` = median distance between adjacent LINKs #3–#6
in the k8 units; ratio = `sep_long / sep_trained`. Result slots have zero context (`:295-301`), so
there is no "result position" geometry to measure. Geometry alone decides nothing (GPT-6 Pro's own
caution); it is read together with the margins logged by probes B and C.

## 5. Numeric thresholds (fixed now)

Per checkpoint:

- **R1(d)** "STOP right on handed prefixes at depth d": operation+subject strict ≥ 61/64 on both
  `kd-prac` and `kd-held`. (61/64 is GPT-6 Pro's own rule.)
- **R2** "early attribute dominates": Probe A `OP_EARLY_ATTR` ≥ 48/64 on `k8-held`.
- **R3** "operation pointer is the only defect": operation-only strict ≥ 59/64 on `k8-prac` and
  `k8-held`. (59/64 is the project's cell mark, `CELL_MARK`.)
- **R4(d)** "subject pointer is a defect": operation-only strict < 59/64 and R1(d) holds, same depth.
- **R5** "premature STOP survives a handed prefix": operation+subject `STOP_EARLY` ≥ 16/64 on
  `k4-held` or `k5-held`.
- **R6** "call-count rule": Probe C condition S3 gives `REL` ≥ 48/64 on `k8-held`.
  **R6′** "position-following": S3 gives `NEXT` + other LINK ≥ 48/64. Otherwise "mixed".
- **R7** "geometric saturation flag": ratio ≤ 0.10 AND median |logit margin between adjacent
  not-yet-used LINKs| ≤ 0.01 at step 2 of condition S0.

Per family (three seeds): a condition "holds for the family" at ≥ 2 of 3 seeds, and every seed is
reported individually; nothing is averaged.

**Positive control (read first; if it fails, nothing else is read).** On the fresh units the v4
checkpoints must reproduce what `diagnosis.json` and `transcripts.json` already show: R1(4) in
12/12; R2 in at least 5 of the 6 learned-position checkpoints; R3 in 3/3 `ctx`; subject-only
strict ≥ 59/64 on `k8-held` in at least 2 of 3 `reg`.

## 6. Decision table

| # | Outcome | What it means | What happens next |
|---|---|---|---|
| D0 | Positive control fails | The probe script is wrong | Fix the script; read nothing else. |
| D1 | R1(4) and R1(5) hold in 3/3 seeds of 19-awake, U5 and U8; R2 holds for 19-awake | Same picture as v4: a healthy STOP behind an operation pointer that asks the attribute early | **Stateless-STOP experiment stays VETOED.** 25b section 5 wording becomes the ledger wording. The one licensed training experiment is 25b step 3 (`ctx` arm ± a self-written "already used" mark), registered separately. |
| D2a | R5 holds for 19-awake (≥ 2/3 seeds) | A real premature STOP exists in the cap-8 family that v4 did not have | The stateless-STOP two-arm experiment becomes **licensed for that family only**, with the code corrections of 25b Problem 3 (head = `Linear(64, 2)`, 130 parameters replacing 66; β₂ = 0.99; controller's own 32-wide token table). It then replaces 25b step 3. |
| D2b | R5 holds for U8 but not for 19-awake or U5 | Long practice under a per-call cost damaged STOP itself | STOP-head experiment still not licensed (the architecture was fine before the continuation). Licensed instead: one cost-arm continuation (0.01 vs 0), with a padding plan, because cost 0 is known to bring back padded short episodes (v3 `abl-cost0`). |
| D3 | R4(6) holds for U5 or U8 | After practice pushes the operation pointer out, the register/subject pointer is the limiter | No further practice-length waves on `reg+ctx`: the arm mixes two defects. Any such work moves to `ctx` (operation pointer alone) or `reg` (subject pointer alone). |
| D4 | R6 for v4-`ctx` | "Counts calls" is the accurate description | The step-3 registration must forecast honestly that a learner that counts may ignore the new mark; a null there is informative. |
| D4′ | R6′ for v4-`ctx` | "Follows positions, loses them with depth" is the accurate description | Read R7. If R7 also holds, the position encoder is upstream and the step-3 candidate is reconsidered (a used-mark does not need position order, so it still stands; a pure "better positions" fix is the rival). |
| D5 | None of the above cleanly (mixed seeds) | No single account | Report per seed; no training experiment is licensed from this probe; the toy-track dispatcher line pauses behind M1 and the concept toy. |

**What the U5/U8 checkpoints add that v4 cannot.** (1) Whether practice moved the operation
pointer's jump or merely exposed the second defect (D3). (2) Whether the two collapsed U8 seeds
(exactly 2.0 and exactly 3.0 calls) collapsed in the operation pointer with STOP intact, or in STOP
(D2b) — the only place where GPT-6 Pro's "call cost → stop early" account could still be literally
about STOP. (3) Whether STOP's correctness on handed prefixes extends to depth 8 *better* after
8-call practice than after 5-call practice (R1(8), reported per seed), which says whether STOP
generalises by result type or by practised depth.

## 7. Claim limits

1. A forced action never counts as an autonomous success. Every number from probes B and C is a
   diagnostic of one component with the others handed to it.
2. Probe C puts the controller in reachable but unpractised states; its results are circuit
   interventions, not task performance. GPT-6 Pro's stated risk (misleading effects off the
   familiar state distribution, its 0.25) applies; hence its rule is kept: a reading needs
   agreement between the free-run fault type (Probe A) and at least one intervention.
3. Everything here is descriptive development evidence on throwaway units. It changes no
   registered result (v3, v4, 19, 19b all stand as filed) and licenses no claim about a system.
4. The probe can license at most one training experiment, which needs its own registration,
   forecasts and hashes.
5. 19/19b D (103,351 parameters with the operator) is not parameter-matched to the 94,629
   baseline; no D-versus-T statement is made.

## 8. Wall-clock

v4's `score --diagnose` (25 cells × 5 kinds × 2 operators) took about 35 s per checkpoint. This
probe: 10 cells × (5 kinds + 3 offset conditions on 2 cells) + geometry, 21 checkpoints (24 with
the optional family): **estimated 10–15 minutes, one thread**, hard stop at 25 minutes. It is
invoked one checkpoint at a time (about 1 minute each, independent, resumable), with
`OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1` and
`/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B`.
It uses one of the Mac's six slots, never BensPC, never cloud, and does not start while a
registered wave needs the Mac quiet.

## 9. Builder's task list

1. New script `scripts/fable_probe26_fault_localisation.py` (additive; imports V1/V3/V4 and the
   experiment-19 trainer module; edits none of them). Sub-commands: `panel`, `probe --ckpt … --family …`, `report`.
2. `panel`: build the 640 units with namespace `fable-probe26-v1`; write them, their sha256, and
   the code hashes of section 2; refuse to overwrite.
3. `probe`: verify the checkpoint sha256 against section 2 before loading; refuse on mismatch.
   Load v4 runs with `V4.load_checkpoint`, 19/19b runs with `TR.load_run_checkpoint(path, 'D')`.
   Assert `model.flags()` matches the family's arm.
4. Implement Probe A's classifier as a pure function over (transcript, chain, status, pointers)
   with unit tests for each of the eight categories, including the order of precedence.
5. Implement Probe B with `V3.intervention_policy` unchanged, passing `record=[]` and `gates=[]`.
6. Implement Probe C's policy as a new local function with the same signature as
   `intervention_policy`'s inner `policy(step, tokens, results, n_results)`; it returns forced
   `subject` and `operation` with mask `step < 2` only, and never forces STOP. Unit test: under S0
   it reproduces `force_operation+subject` for the first two steps exactly.
7. Implement Probe D from `model.question_context`; skip for arms without learned positions.
8. `report`: per-checkpoint tables, the R1–R7 flags, the positive-control verdict first, then the
   decision-table row(s) that fire. No averaging across seeds.
9. Tests in `tests/test_fable_probe26.py`. Output folder
   `artifacts/fable-probe26-20260920/` (or the run date). No commits.
10. Before the first `probe` call: record this file's sha256 and copy P102–P111 into the ledger.

## 10. Auditor's checklist

- [ ] This file's sha256 and the ledger entries P102–P111 predate the first probe output (file times and the panel manifest).
- [ ] All 21 (or 24) checkpoint hashes equal section 2; operator hash equals section 2; code hashes unchanged since `panel`.
- [ ] Panel namespace is `fable-probe26-v1`; no unit was read from the v3 registered panels, the exp-19 dev panels, or any confirmation suite.
- [ ] Every rollout greedy; evaluation cap 16; single thread.
- [ ] Positive control evaluated and reported before anything else; if it failed, nothing else was interpreted.
- [ ] Under every forced kind, forcing stops at `step == hops` (Probe B) or `step == 2` (Probe C); STOP is never forced except in the `force_stop` kind.
- [ ] Native logits in `record` are the model's own (taken before the forced overwrite) — check one unit by hand against an unforced run with the same prefix.
- [ ] No number from a forced run is described as the controller succeeding.
- [ ] Every seed is listed; no averages across seeds; thresholds are exactly those of section 5.
- [ ] The report names which decision row(s) fired and does not license more than one training experiment.
- [ ] Oracle-operator runs agree with trained-operator runs on the fault category (operator error is not the story); any `OPERATOR` count above 2/64 in a cell is flagged.

## 11. Forecasts (continuing the ledger from P102; reviewer's own, made before any probe was run on the 19/19b checkpoints)

| # | Statement | Probability |
|---|---|---|
| P102 | The positive control passes (section 5) | 0.90 |
| P103 | R1(4) and R1(5) hold in all three 19-awake checkpoints | 0.72 |
| P104 | R1(8) holds in all three 19-awake checkpoints | 0.35 |
| P105 | R2 (early attribute ≥ 48/64 on k8-held) holds in at least 6 of the 9 19/19b checkpoints | 0.78 |
| P106 | R4(6) holds for U8 seed 1902 (operation-only strict < 59 on k6 while operation+subject ≥ 61) | 0.65 |
| P107 | R5 (premature STOP on a handed prefix at k4/k5) holds for at least one 19/19b family (≥ 2/3 seeds) | 0.15 |
| P108 | In both collapsed U8 checkpoints (seeds 1900, 1901), operation+subject strict on k4-held is ≥ 61/64 (the collapse is in the operation pointer, STOP intact) | 0.60 |
| P109 | R6 (S3 still gives the attribute, ≥ 48/64) holds in at least 2 of 3 v4-`ctx` checkpoints | 0.55 |
| P110 | The geometry ratio is ≤ 0.10 in at least 2 of 3 v4-`ctx` checkpoints | 0.40 |
| P111 | Operation-only does NOT rescue k8-held (strict < 59) in all three 19-awake checkpoints | 0.85 |

Outside forecasts recorded for scoring alongside: GPT-6 Pro Problem 1 prediction 1 (0.65) — already
FALSE on the v4 score-time diagnosis, to be re-confirmed by P102's control; its rival "third
operation is already an incorrect attribute lookup" (0.30) — supported; its Problem 3 "most likely
failure … attribute too early" (0.45) — moot while the experiment is vetoed.
