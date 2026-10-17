# Plan-assembly solve: bracket test results and what the step-4 dead zone actually is (Sat Oct 17, 2026)

Opus 5.5 Ultracode solve session for Muse's packet "the plan-assembly problem (the step-4 dead zone)". Zero training, $0, free cloud CPU.
Checkpoints: `results/far-transfer/learn/L13-LBsoft10/step_4000/checkpoint.pt` (sha256 `b10f7917...7a7b`) and `L14-LBnk30` (`318ac36c...1f406`),
taken from branch `claude/launch-bound-solve`. Both hashes were re-checked against `results/far-transfer/learn/MANIFEST.md`.
Inputs: `train-rows-l5.jsonl` (`15cda9d3...`), `eval-rows-l5.jsonl` (`2d927fdb...`), `sheet-probe.jsonl` (`5a560b5d...`), all from branch `claude/far-transfer-inputs`.
Code: branch `claude/project-thread-94a956` at `4d294b665` (the R1 commit).
Labels: **shown** = measured here, **suggested** = reasoned, **untested** = never run.

## 0. The answer in one paragraph (for Ben)

The dead zone is not about step 4, and it is not about handing off from one piece to the next.

All 106 dead-zone questions contain one particular kind of piece: cell arithmetic such as `B2+B3*2`. Inside a multiply join, `(B2+B3*2)*(MAX(...))`, that piece needs the brackets to mean "do this whole thing first". The model never saw brackets change the order around a `*` in training. Instead, 186 training rows of the form `B2+B3*2*MAX(...)` (no brackets) taught it the opposite grouping, so it runs the unbracketed program.

When cell arithmetic is the first piece, the model never writes the final multiply: 0 of 120 under teacher forcing. Change only the `*` join to `+` and it gets that call right 95 of 120 times.

Separately, the cell-arithmetic piece is the weakest piece kind everywhere. It scores 22% even as a single formula, against 66% for other kinds.

"Step 4 with 4 cells" is simply where a 2-call, 2-cell cell-arithmetic piece lands in `(K)*(J)`.

Neither loss-weighting lever (B3's transition weight or R1's first-call weight) can supply a rule that has zero training examples. A data change that teaches brackets over `*` outside the held-out join can.

## 1. Packet claims checked against the code and the record

| packet claim | verdict | evidence (shown unless marked) |
|---|---|---|
| 4-step / 4-cell HO stratum is 0/106 on both runs; unconditioned step-4 is 2/139 (L13), 0/139 (L14) | **Reproduced exactly** | Regenerated per-item dumps (`dump_items`, hit counts equal both `scores.jsonl` rows at step 4000). "4 leaf operands" = 4 grid cells referenced, counting a range's cells (this definition gives 106 of 139). |
| "It is the model failing to START the next piece correctly at the handoff" | **Wrong** | Dead-zone first wrong call: K's first call (round 0) **83/106 (L13), 86/106 (L14)**; J's first call (the handoff) **11/106** on both. |
| B1/B2: completion 96.9% from a correct prefix vs assembly 4.3%, therefore "assembly ≠ completion" | **The contrast does not exist mechanistically** | Free-run call k equals the teacher-forced call k on **2,927/2,927 (L13) and 2,828/2,828 (L14)** eligible calls, 100% exact strings. The model's state depends only on the prompt and the tape, so continuing a handed prefix *is* assembling it. The B1 definition is not in any branch I can reach (`/mnt/project-files` only), so 96.9% could not be re-derived. Under teacher forcing, the join call on dead-zone items with cell arithmetic in K is **0/60**, so 96.9% cannot be the join call on this stratum. It is probably measured on items whose free-run prefix was already right (selection) or on the answer step after a full tape. |
| The step-4 data hole is refuted (1,645 joined 4-step rows) | **Right at step-count granularity, wrong at the granularity that matters** | 1,645 is reproduced (train joins by `n_steps`). But the training rows contain **zero** formulas where brackets override `*` precedence. 626 rows have a grouping bracket (all `(K)+(J)` / `(K)-(J)`), and none has a bracketed group under a depth-0 `*`. They contain **186** `K*J` rows teaching the opposite grouping (171 with cell arithmetic as K, 15 as J). |
| (K)*(J) never trained | **Right**, and it matters only for the cell-arithmetic slice | HO without cell arithmetic: **59/294 = 20.1% (L13), 41/294 = 13.9% (L14)**. HO with cell arithmetic: **0/126 on both**. Every HO hit comes from the non-cell-arithmetic 70%. |
| R1 trainer: "the effective learning rate is unchanged across arms" (`install_first_call_weight` docstring) | **False on these checkpoints** | Both checkpoints are span-copy models (`cfg`: `span_copy`, `span_idx`, `span_end` all True). In `span_terms` only round 0 is rescaled (`renorm × weight`) and rounds ≥ 1 stay at 1 (`learn_probe.py:1422-1430`), so the per-trace span-loss total grows: at weight 3 on a 4-call trace, 2.0 + 1 + 1 + 1 = 5 vs 4 (+25%). `call_loss` is renormalised on every round and is preserved. R1 as committed is two changes on span models. **This needs a coordinator ruling before R1 books.** |

## 2. Mechanism theories, ranked, each with its discriminating prediction

**T1. Bracket blindness under a conflicting precedence rule (lead; shown).** In `(K)*(J)` with a cell-arithmetic piece, the model ignores the brackets and runs the program it learned from the 186 unbracketed `c1+c2*N*J` training rows.
- *Prediction unique to T1:* change only the join from `*` to `+` (a trained bracketed layout). The calls that differ between the bracketed and unbracketed programs recover. Calls that are the same in both programs (J's first call, `mul c2 N`) do not.
- *Result (shown):*

| teacher-forced call | `(K)*(J)` L13 / L14 | `(K)+(J)` L13 / L14 |
|---|---|---|
| join call, cell arithmetic in K (n=120) | **0 / 0** | **95 / 95** |
| cell-arithmetic `add`, cell arithmetic in J (n=152) | 5 / 2 | 19 / 18 |
| J's first call, cell arithmetic in J (n=152) | 23 / 16 | 21 / 8 |
| whole items right (n=272) | 0 / 0 | 10 / 5 |

- What the model writes instead (shown):
  - With cell arithmetic in K, at the join it writes `add` 70/120 (L13) and 79/120 (L14), `noop` 44/40, and never `mul`. Its operands are K's value and J's value, both right. Only the operator follows the training rule, whose last call is `add c1 …`.
  - With cell arithmetic in J, at the piece's `add` call it writes `mul` 115/152 (L13), 70 of them with K's result as an operand. That is the training program for `K*c1+c2*N`.
- Bracket blindness also shows on single formulas (shown). `(c1+c2)*N`, built from the probe's 240 `c1+c2*N` items, scores **1/240 (L13), 0/240 (L14)** against 27/240 and 17/240 unbracketed. The model usually starts with a `mul` anyway.
- Coverage: on its own, T1 makes the 60 dead-zone items with cell arithmetic in K unsolvable, and the CA-add call of the other 46 nearly so.

**T2. Cell-arithmetic operand binding is weak in every frame (shown; second cause, frame-independent).**
- With a correct prefix, the piece's first call `mul c2 N` is right 38% (L13) and 32% (L14) on single formulas, and 20-32% inside joins.
- Errors: `c1` in place of `c2` (the cell before the `+`) about 35% on singles; another grid cell 25-30%.
- Hit rates for cell arithmetic:
  - single formulas (F0-near): 21.7% vs 66.4% for other kinds (L13)
  - in-distribution `K+J` joins: 3.8% (S)
  - training-sample rows (`fit`): 8.8%
  - so it is underfit even on rows it trained on.
- *Prediction unique to T2:* J's first call stays weak when the frame conflict is removed. Confirmed: 23 → 21 and 16 → 8 of 152 in the counterfactual.

**T3. Piece-start calls are the weak calls in general (shown; the general far limiter, not dead-zone-specific).** Teacher-forced accuracy on HO items without cell arithmetic (L13; L14 in brackets):

| call | accuracy |
|---|---|
| K's first call | 53.7% (48.3) |
| later K calls | 79.5% (74.0) |
| J's first call (the transition) | **38.1%** (34.4) |
| later J calls | 92.7% (89.5) |
| join | 73.1% (61.2) |

The transition is the weakest call in every cell, including the trained `K+J` layout (S: 45.0%).
- Errors are address-resolution near misses. Of wrong operands not referenced by the formula, 52-54% are an adjacent row and 30-35% the same row in the other column.
- Cross-piece leakage is common: 51-54% of K's wrong first-call operands are one of J's cells.
- *Prediction unique to T3:* weighting the transition (B3) raises HO on items without cell arithmetic but cannot touch the 60 dead-zone items with cell arithmetic in K. This is untested and is B3's actual testable claim.

**T4. Own-history / exposure bias ("assembling yourself differs from continuing a handed plan") (refuted, shown).** It predicts that free-run calls after a correct prefix differ from teacher-forced calls. They agree on 100% of 5,755 eligible calls across both checkpoints.

**T5. Step-count data hole / step-4 surface form (refuted, shown).** The 0/106 stratum is a piece-kind stratum. All 106 contain a `c+c*N` piece, and every HO item with such a piece scores 0 (126/126), at 4, 5 and 6 steps alike.

## 3. The $0 bracket test, as specified and run

- **What it brackets:** for each item, the calls on either side of the K-to-J handoff:
  - round nK-1 (last K call)
  - round nK (J's first call)
  - round nK+1
  - plus K's first call and the join call, all teacher-forced (the tool's own working on the tape, `p2_diag.teacher_forced`).
- **Groups:** split by cell arithmetic present/absent and in K/J.
- **Validity checks:**
  - determinism: the free-run call equals the teacher-forced call whenever the free-run prefix is right
  - product: the teacher-forced all-calls-right rate matches the free-run all-calls-right rate (L13 11.9% vs 12.4%; L14 9.0% vs 8.8%)
- **Checkpoints:** L13/L14 step 4000 above.
- **Cells:** HO, HPO, S, HP, F4-two (2,100 items per checkpoint, 0 skipped).
- **Runtime:** 29 s per checkpoint.
- **Script and tables:** `results/far-transfer/plan-assembly-2026-10-17/` (`bracket.py`, `bracket-L13/L14.{txt,json}`; the other probes and how to rebuild the inputs are in its README).

Caveat: the K/J role labels are exact only for bracketed layouts. In unbracketed `K+J`/`K*J` with cell arithmetic in J, the tool's precedence order interleaves the pieces.

**Outcomes, and what each rules in or out:**

| possible outcome | would mean | observed |
|---|---|---|
| Break at nK only (last K call fine, J's first call low) | handoff assembly (packet's theory) → B3 | Partly. J's first call is the weakest call in general (T3), but it is not where the dead zone breaks. |
| Break at round 0 | start of the first piece → R1 | Free-run first errors in the dead zone are 78-81% at round 0. Under teacher forcing, round 0 on dead-zone items with cell arithmetic is 25-27%. |
| A call that is 0% under teacher forcing | a rule failure, not a noise failure | **Yes.** Join op with cell arithmetic in K in `(K)*(J)`: 0/120. CA add with cell arithmetic in J: 2-5/152. Both are T1. |
| Free run ≠ teacher forced after a correct prefix | own-history effect (T4) | No: 100% agreement. |

## 4. B3 run design (house form). My call: do not run B3 as the dead-zone fix

**Prediction (suggested):**
- B3 cannot pass success condition 1: about 60 of the 106 dead-zone items need a `mul` join the model writes 0/120 times in this frame, and no training row rewards it.
- It can pass condition 2 through T3, since the transition is the weakest call on the 294 HO items without cell arithmetic.

If Muse still wants B3 measured as a general far lever, this is the card:

- **Change (one):** add `--transition-weight W` on J's first call. It needs a definition the packet lacks: the transition is the first round whose call uses a J-piece grid reference. Rows whose tool order interleaves K and J (unbracketed `K+J`/`K*J` with cell arithmetic in J) get no transition weight. F0-near single rows get none.
- **Renormalisation:** per trace as in R1, but on **both** `call_loss` and `span_terms`. Otherwise it inherits R1's +25% span-mass confound (§1).
- **Arms:**
  - A0 = the L13 recipe exactly: LB, `--guard kfsoft --guard-soft 10`, KL 10x on 32 replay rows, lr 1e-4, 4,000 updates, batch 64, L5 rows.
  - A1 = A0 + `--transition-weight W`, with W equal to R1's first-call weight so the two levers are compared at equal strength.
- **Seeds and pairing map:** seeds 201-206. (A0, s) ↔ (A1, s), with the same parent, data order and replay draws via `--seed`. If R1 runs from the same commit on the same seeds, A0 *is* R1's control and B3 adds only 6 runs; that sharing must be in the map before booking.
- **Bars** (fixed before any run trains; d = A1 − A0 per seed, σ_d = SD of the 6 paired d, half-width = t(5)·σ_d/√6 = 1.05·σ_d):
  1. Dead-zone cell: mean A1 ≥ **4/106** AND d̄ ≥ +3 items AND d̄ − 1.05σ_d > 0; unconditioned step 4 (139) d̄ > 0. The 4/106 level is taken from the bracket test: removing the frame conflict alone gave 10/272 = 3.7% (L13) on cell-arithmetic items.
  2. Whole HO: d̄ ≥ **+10/420 (+2.4 pts)** AND d̄ − 1.05σ_d > 0. 59/420 is the L13 single-run reference only; the bar is paired.
  3. No other step count worse: for each of 3, 5, 6-7 steps, d̄ ≥ −max(1.05σ_d, 1 item).
  4. Proved wrong: dead-zone mean A1 ≤ 1/106, or HO d̄ − 1.05σ_d < 0 with d̄ ≤ 0.
  5. Unpowered (neither pass nor fail): 1.05σ_d > the margin.
- **σ_d:** no continue-train σ_d exists. The goal's rule (σ_d from the run's own paired differences) makes the bars computable at readout. The measurement that must exist first is the A0 seed replicate set, which R1's control arm produces.
- **Venue and cost:**
  - One L13-recipe run measured 18,597 s training + 2,177 s measuring = 5.8 h on 4 CPU threads.
  - A Vast 32-core host is $0.095-0.20/h today (read-only offer query): 8 concurrent 4-thread runs, about 12 h with a 2x slowdown margin.
  - 12 runs ≈ 2 batches ≈ 24 h ≈ **$2.5-5**; 6 runs if A0 is shared ≈ $1.5-2.5.
  - Hard stop $8. Inside Vast's $50/week cap. A bid to the coordinator, not a booking.

**What I would bid instead as the dead-zone candidate (BX, untested; separate card, one change):**
- **Change:** replace 600 of the 6,000 F0-near single-formula rows (10%, same kind quotas otherwise) with bracket-overrides-precedence single formulas: `(c1±c2)*N` and `N*(c1±c2)`, tool working from `sheet.evaluate`.
- **No join rows are added**, so HO `(K)*(J)` stays held out.
- **Discriminating predictions:**
  - bracketed singles go from 0-1/240 to ≥ 50%
  - the teacher-forced join op on HO with cell arithmetic in K goes from 0/120 to ≥ 30%
  - the dead-zone cell reaches ≥ 4/106
- **If the teacher-forced join op stays ~0/120 after BX fits the bracketed singles, T1 is wrong.**
- Same arms/seeds/bars template as above (A0 shared).

## 5. Further $0 probes, each with the theory it discriminates

| probe | discriminates | status / cost |
|---|---|---|
| Join-op counterfactual `(K)*(J)` → `(K)+(J)` on the cell-arithmetic items | T1 vs T3 | **Run** (§2), 1 min |
| Bracketed singles `(c1+c2)*N` vs `c1+c2*N` | T1 (bracket blindness) beyond joins | **Run**, 1 min |
| Operand-order rewrite `c1+c2*N` → `c2*N+c1` (same value) | T2: first-position binding vs address resolution | untested, 1 min. Check it is not out-of-form first. |
| Cross-piece leakage: replace J by a piece with cells disjoint from K's, and by a constant-only piece; measure K's first call | T3 interference (predicts K's first call rises toward K-alone 66%) vs pure address noise | untested, 1 min |
| Prefix-corruption curve: teacher forcing with one tape entry replaced by a wrong value at distance 1, 2, 3 before the probed call; measure copy-of-corrupt vs recompute | whether later calls read the tape or re-derive from the formula; whether J's first call fails from tape distraction | untested, needs a 10-line gold-tape edit before `make_row`, 2 min |
| Per-round teacher-forced loss on `fit` rows with cell arithmetic | whether T2 is underfitting (high loss on training rows, so loss weighting at that call could help) or a capacity limit | untested, 1 min |

## 6. Kill list

- **Kill:**
  - B3 as the lead dead-zone fix. Keep it only as a general T3 lever, ranked behind R1.
  - The "assembly vs completion" line, including any scheduled-sampling or own-history work. Determinism makes them the same computation.
  - Any further step-count stratification of the far task.
  - Reading B1's 96.9% as "the model can finish plans".
- **Keep:** R1 booked. Round 0 is the dead zone's first-error round and the second-weakest call in general. But rule on the span-term asymmetry first.
- **Left open on purpose:**
  - why piece-start calls resolve addresses so loosely (T3)
  - whether bracket semantics learned on singles transfer into the held-out `(K)*(J)` join (BX's real question)
  - the B1 definition (record not reachable)
  - σ_d for continue-train contrasts
  - whether the 186 conflicting `K*J` rows should stay. They are correct arithmetic. Removing them is a different, untested change.

## 7. First action, and the result that would prove this framing wrong

- **First action:** get the coordinator's ruling on R1's span-term renormalisation before R1 trains. It is booked first in week 1, and its control arm is everyone's σ_d. Then file BX's run card as a bid.
- **What would prove this wrong:** B3 (transition weight alone) lifting the dead-zone cell to ≥ 4/106 on paired seeds. T1 says 60 of those 106 items cannot succeed without a `mul` join the model writes 0/120 times in this frame, and nothing B3 changes rewards that call.
