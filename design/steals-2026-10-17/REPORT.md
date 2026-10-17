# Eight frontier steals in Premonition-mini: implementation report

Written 2026-10-17 (UTC). **Status: DRAFT for the coordinator's code review.** No training beyond tiny CPU smoke
runs, no GPU, nothing booked.
- Branch: `claude/steals-8`, based on `main` at 73b8e0224.
- Build contract: [`SPEC.md`](SPEC.md).
- Raw numbers: `artifacts/claude-steals-20261017/` (`costs.json`, `qk-diagnostic.json`, `muon-bench.json`).

Labels: **shown** means measured here; **suggested** means my reading of a measurement; **untested** means not measured.

## 0. Read first: what the repo shows that the commission assumed

| # | Commission assumes | What the repo shows | Consequence |
|---|---|---|---|
| F1 | a "current model" for the QK diagnostic | **No PremonitionMini checkpoint exists** in the tree, the git history or the BensPC notes (survey 10-17, same finding as PR 79). | The diagnostic ran on tiny D trained on the far-fact toy for 425 steps (130 s CPU). It shows what D learns early, not what a funded run learns. |
| F2 | D is a working model to improve | The toy result **reproduces here** (shown): gold recall@4 is 0.90, but answer accuracy is 7.4% against 6.25% chance, **and 7.4% with the gold cards handed in**. The 09-18 trainer handoff says the same. | Retrieval works and the answer path does not. Steals that act on the answer path come first in the A/B order (§5). |
| F3 | three steals add something new | **Parts of three already exist** (shown by reading the code):<br>• The binder `s + σ(g)(tanh c − s)` is already a gated delta rule whose readback is the identity.<br>• ASK already matches by direction: the query and the keys are unit vectors, scaled by a learned κ.<br>• The NULL card plus the ASK-logit BCE is already a way to "attend to nothing". | Each of these steals was built as the part that is actually new: key-addressed readback, learned per-dimension gains, and a sink logit with its own target. §2 has the details. |
| F4 | ASK reuse saves compute | ASK scoring is 2·dk·(L+1) ≈ 13k multiply-adds per (question, loop). The think block is ≈ 60M. | Steal 7 can only change behaviour, never cost, at this size (shown in §1: counted FLOPs −0.01%). |
| F5 | Engram is a neutral capacity add | Hashing **name spellings** gives D a parametric memory of specific names. The project's design keeps facts in the notebook and starts it empty, and village names repeat across worlds. | **Coordinator ruling needed** before any Engram A/B. If it is run, the held-out split must have names disjoint from training, or a gain could be name memorisation. |
| F6 | editing `premonition/` is fine | `handoff/HANDOFF.md:33` forbids edits under `premonition/`. | Edited under Ben's Oct 17 commission (as PR 79 was). The coordinator should confirm the override. |
| F7 | this lands alone | PR 79 (`decoder_reader_kv`) and PR 82 (span cards) edit `model.py` and `config.py` from the same base. | The merge order needs a decision. Expect conflicts in `Decoder.forward` and the `MiniConfig` field block. |

## 1. Summary per mechanism

D = 2,013,140 parameters at d = 128 with the v1 vocabulary. The cost columns come from
`scripts/premonition_steals_costs.py`: 4 synthetic visits × 40 lines, CPU, 1 thread, median of 7 steps (forward +
backward).
- "FLOPs" is the FlopCounterMode count (matmuls and attention only). Gates, norms and hashing are elementwise, so
  they are not counted.
- **The time noise floor is about ±4–10%.** The same all-off model, timed a second time, gives −3.5%, −3.7% and
  +3.6%. Read any step-time change inside ±10% as noise.

| # | Steal | Flag(s) | Params Δ | FLOPs Δ (gold/teacher/own) | CPU step time Δ (gold/teacher/own) | Tests |
|---|---|---|---|---|---|---|
| 1 | Delta-rule erase-then-write bind | `delta_bind` | **−60,903** (the binder is replaced) | −0.04 / −0.06 / −0.03% | −7.6 / +2.5 / +4.5% (noise) | 13/13 |
| 2 | Gated fetch | `fetch_gate` | +1,544 | +0.02 / +0.01 / +0.09% | −5.6 / +0.5 / +10.3% | 22/22 (with sinks) |
| 2 | Per-head sink | `fetch_sink` | +5 | ≈ 0 | −9.7 / −0.9 / +3.6% (noise) | (same file) |
| 3 | Attention residuals across loops | `loop_attnres` | +1,024 | 0 | −7.0 / −0.4 / +4.7% (noise) | 11/11 |
| 4 | Engram hashed name lookup | `engram` | **+164,096 (+8.15%)** | +0.09 / +0.05 / +0.03% | +1.6 / −1.2 / −0.2% (noise) | 16/16 |
| 5 | Per-register halting | `row_halt` | +129 | ≈ 0 | −4.9 / −4.2 / +6.7% (noise) | 23/23 (with depth) |
| 5 | Random-depth training | `random_depth` | 0 | own **−34%** (fewer loops) | own **−35%** | (same file) |
| 6 | QK-norm on ASK (gains) | `qk_norm` | +128 | 0 | −6.9 / −4.9 / +5.4% (noise) | 19/19 (QK family) |
| 6 | QK-norm on all attention | `qk_norm_all` | +320 | 0 | +3.5 / **+24.2 / +23.4%** | (same file) |
| 6 | QK-Clip on ASK | `qk_clip` (τ, 0 = off) | 0 | 0 | noise | (same file) |
| 6 | Content + line-position sub-keys | `key_split` | 0 | 0 | noise | (same file) |
| 7 | ASK-selection reuse | `ask_reuse` | 0 | −0.01% | noise | 8/8 |
| 8 | Muon optimiser | `MiniTrainer(optimizer="muon")` | 0 | 0 | optimizer step 6.5× AdamW's: +39 ms on a ≈ 0.49 s step (**+8%**, CPU d = 128) | 21/21 |

- `random_depth`'s −34% is the sampled cap at seed 0 cutting own-mode loops. It is a training-cost change, not a
  per-loop cost.
- `qk_norm_all` is the only flag whose per-step cost is clearly above noise. On CPU, `RMSNorm` runs unfused under
  autocast.

**Swap condition, shown.** With all flags off, the model is bit-identical to 73b8e0224
(`tests/test_premonition_steals_identity.py`).
- The test loads 73b8e0224's `model.py`, `store.py` and `train.py` from git and compares with `torch.equal`.
- What it compares:
  - init, and the RNG state after construction
  - all three training modes: every loss, metric and gradient
  - `answer()` with no wipe, a store wipe and a full wipe
  - `answer_with_gold`
  - trainer steps in the gold, teacher and own phases: losses, grad norms, card stats, final weights and AdamW
    state
- Coverage: D, D-noask and D-noptr, seeds 0 and 1, plus full-size init.
- The test fails on a 1e-7 weight perturbation, so it is not vacuous.

**Composability, shown.** Each flag alone, and all flags together, builds, trains every mode with finite losses and
gradients, answers, and takes trainer steps. The hand parameter count equals the modules' count. The two controls
(D-noask, D-noptr) take every flag.

**Paired init, shown.** Steal modules are built and initialised off the global RNG stream (`model._aside`). So at a
given seed, every shared weight and the RNG state equal the flag-off model's, and a paired A/B differs only in the
steal. The exception is `delta_bind`: it removes the binder, so the binder's draws, and every weight after them,
move.

**Suite, shown.** All 103 test files were run one by one on this branch and on an untouched `main` checkout.
- Every pre-existing file has the same outcome on both.
- The 9 new files (143 tests) all pass.
- Pre-existing non-passes are environmental and identical on both:
  - 10 fable files assert a hard-coded Mac path;
  - `test_remote_runner` has 1 error;
  - `test_premonition_interface_probes` needs missing artifacts;
  - 38 files collect no tests in this checkout.

## 2. What was built, per mechanism

**1 · `delta_bind` (Gated DeltaNet, KDA).** It works on the slot read as a matrix S = s.view(8, d/8). The address is
κ = normalize(W_a k_card), using the fetched card's own unit key (new `CardStore.gather_keys`). The write is:

S ← S + σ(β) κ (tanh w − κᵀS)ᵀ

with [β, w] = W_w [s; v]. The slot therefore stores the correction along κ, and the directions orthogonal to κ keep
earlier cards. That is the new part: today's binder overwrites a gated share of the whole slot.
- Tests:
  - A slot that already reads back w is a fixed point.
  - Writes along orthogonal addresses both read back.
  - Gradients reach `delta_*`.
- Note: w depends on [s; v] (same inputs as the old binder), so "the same card twice" is not an exact no-op in the
  full network.

**2 · `fetch_gate`, `fetch_sink` (Qwen gated attention, gpt-oss sink).**
- **Gate:**
  - Fetched card values are multiplied by a per-head sigmoid of W [normed register 0; value], broadcast over each
    head's channels. The gated value feeds both the card row and the slot bind.
  - The decoder's cross-attention output is multiplied by a headwise sigmoid of the query-side normed state.
  - Both gates start open (bias 3, σ = 0.95).
- **Sinks:**
  - The decoder cross-attention gets one learned logit per head, implemented as a zero key and value with logit
    b_h. A head can now put its mass on nothing.
  - ASK gets one sink logit, because ASK has one head. "Per head" therefore reduces to one scalar there.
  - The ASK sink sits in every set-CE denominator. Questions with nothing left to fetch take it as their target
    (otherwise the loss can only push it down).
  - `_choose` drops cards that score at or below it. It starts at −κ_init, a no-op.
  - The NULL card stays.
- With the ASK sink on, L_ask's set term averages over all rows, not only the rows that still need cards, so its
  magnitude changes.

**3 · `loop_attnres` (Kimi AttnRes).** Loop t's registers are Σ_i α_i v_i over the register states entering loops
0..t, with α = softmax_i(q_t · norm(v_i)), per register row.
- q_t is zero-initialised (Kimi), so the mix starts as a uniform mean. Loop 0 is unchanged.
- **Only registers are mixed**, which is the commission's "register states" read literally. Card rows are first in,
  first out and slots are rewritten by binds, so mixing old copies of those would blend evicted cards into new ones.

**4 · `engram` (Engram).**
- Four hash heads × 1,024 rows × d/4, plus W_K and W_V.
- Keys are each line's **name spellings** (`batch.names`), hashed with blake2b. ENT ids are per-visit variables, so
  hashing the id would key on slot numbers, not people.
- e is the mean over the line's names. The Engram gate is α = σ(⟨norm p, norm W_K e⟩/√d), and the card value gets
  α W_V e.
- Lines with no name are unchanged exactly.
- Hashing is cached and costs about 0.02 ms warm. The dense lookup adds about 3% to a d = 128 step, which is within
  the CPU noise in §1.
- Parameter cost: **131,072 for the tables + 33,024 for W_K and W_V = 164,096 (+8.15%).** These are real
  parameters at this size and are reported apart from the 1.9M–2.15M band.
- On the toy and the synthetic tests, an id always has the same spelling, so the per-visit-variable property is
  only exercised on village data.
- See F5.

**5 · `row_halt`, `random_depth` (Mixture-of-Recursions, Geiping).**
- **`row_halt`:** each register row has a router p = σ(W norm(r)), with bias −3 so registers keep updating at
  first.
  - keep is soft (Π(1 − p)) in training and sticky-hard (p ≤ 0.5) on the answer paths.
  - A halted register stops updating, r ← r + keep·(Δ), and stays readable as context.
  - If register 0 halts, the question stops fetching.
  - The ponder cost is 0.01 · mean(keep), added to L_halt.
  - Question-level HALT is unchanged.
- **`random_depth`:** each training batch samples a loop cap from U{1..8}.
  - The trainer samples it **before** charging the batch, so FLOP charging matches the loops run
    (`loop_mismatches == 0`, tested).
  - `answer()` is unaffected.

**6 · QK family (Qwen3, Gemma 3, Kimi K2, MLA).**
- **`qk_norm`:** learned per-dimension gains on ASK's unit query and keys. Score = κ⟨g_q ⊙ q̂, g_k ⊙ k̂⟩ + age
  bias. At init it is exactly today's score (tested).
- **`qk_norm_all`:** RMSNorm with a learned weight on q and k, per head, before RoPE, in every attention (reader
  local attention, think layers, decoder self- and cross-attention).
- **`qk_clip` = τ:**
  - Each training forward records the largest κ·cos over eligible real cards.
  - After `optimizer.step()`, κ is scaled by τ/max when it is exceeded.
  - Because ASK is cosine-normalised, κ is its only logit scale, so this is all of QK-Clip for ASK. It is not
    applied to the other attentions, whose logits `qk_norm_all` bounds.
- **`key_split`:** the last dk/4 dims of every card key are RoPE-rotated at the card's line index, and those of the
  query at the question's line.
  - After normalisation, that part of the dot product depends only on line distance. This is MLA's decoupled
    position key, without the rest of MLA.
  - No new parameters.
  - Caveat: under `qk_norm` + `key_split` the gains apply after rotation. Unequal gains within a rotation pair make
    the position part slightly non-relative.

**7 · `ask_reuse` (IndexCache).** Loops 0, 2, 4, ... always rescore, as does any question whose unit query has
moved by cosine distance ≥ 0.1 or that has no cache yet. Other loops reuse the cached scores, with the current
eligibility re-applied: fetched cards become −∞ and NULL stays.
- Inserts, gates and binds are recomputed every loop.
- It is a cache with invalidation, not a frozen fetch: a threshold of 0 refreshes every loop, and the result equals
  the flag-off model (tested).
- No compute saving at this size (F4).

**8 · Muon (Moonshot recipe).** `premonition/muon.py`, class `MuonAdamW`, one optimizer whose param groups carry a
`muon` flag. The trainer's lr schedule and checkpoint state work unchanged.
- **Muon side:**
  - Applies to Linear weights in the reader, `writer.key`, `writer.value`, the think layers and the decoder (except
    `cross_gate`).
  - Nesterov momentum 0.95, then 5 Newton–Schulz steps.
  - The update is scaled by 0.2·√max(A, B) so its RMS matches AdamW, with decoupled weight decay.
- **AdamW side:** everything else: the embeddings and tied head, norms, biases, gates, sinks, gains,
  pseudo-queries, Engram tables, `heads.*` and the binder.
- `MiniTrainer(optimizer="muon")`, `train_toy(optimizer=)`.
- A Muon checkpoint records its optimizer and resumes as Muon (tested). The default `"adamw"` path is
  bit-identical.
- The fused GRU input matrix (z, h̃ and gate in one 128×384) is orthogonalised as one matrix. A split variant is
  untested.

## 3. QK-norm diagnostic, run before QK-norm was enabled in any test

`scripts/premonition_steals_qk_diagnostic.py`, all flags off, tiny D on the far-fact toy, 256 held-out questions.
Each question's own first-ASK top-4 is split into gold and wrong cards. Each toy question has exactly **one** gold
card, so 3 of every 4 fetches are "wrong" by construction. The sharper comparison is therefore the wrong cards that
**outrank** gold, and the paired gap (best wrong − gold) per question.

| trained (425 steps) | gold fetched (n = 231) | wrong fetched (n = 793) | wrong outranking gold (n = 436) | eligible non-gold (n = 8,084) |
|---|---|---|---|---|
| raw key norm ‖W_k p‖, mean / median | 1.989 / 1.935 | 1.973 / 1.909 | 1.993 / 1.919 | 1.526 / 1.366 |
| stored key norm | 1.000 | 1.000 | 1.000 | 1.000 |
| value norm | 6.55 / 6.65 | 6.49 / 6.64 | 6.38 / 6.57 | 4.87 / 4.25 |
| cos(q, k) | 0.980 / 0.992 | 0.933 / 0.992 | 0.983 / 0.992 | −0.230 / −0.350 |
| κ·cos (κ = 12.96) | 12.70 | 12.09 | 12.73 | −2.99 |
| age-bias term | 0.027 | 0.027 | 0.030 | −0.044 |

- **Paired, best wrong − gold** (median): raw key norm +0.006, cos +0.001, score margin −0.014.
- **Gold ranked first: 24.2%** of questions. Recall@4 is 0.902 (random 0.119). The raw query norm is 3.05 for
  every group.
- **At init** (for reference): gold ranked first 4.3%, recall@4 0.203. The raw key norm is 0.18 for gold and 0.16
  for wrong.

**Finding, shown:**
- Stored keys are already unit vectors, so key magnitude never reaches ASK's score.
- The raw (pre-normalisation) norm does **not** separate gold from the wrong cards that are fetched or that outrank
  gold. It only separates fact cards (≈ 2.0) from the rest (≈ 1.5).
- The wrong cards that beat gold are tied with it in direction (cos 0.992 against 0.992) and score (margin −0.01).

**Reading, suggested:**
- Wrong fetches come from key collapse, not from magnitude. Every fact card's key points the same way, so ASK
  separates "fact card" from "filler" but not "which fact".
- QK-norm (direction-only matching) has nothing to recover here, and QK-Clip has nothing to clip: κ is at 13 and
  every eligible card ties.
- Steals that put new information into the key are the ones that could break the tie: `key_split` adds the line
  position, and `engram` adds name identity (but see F5).
- The AdamW toy run is short, so this is how early D behaves, not a converged model (untested).

## 4. Muon against AdamW, short CPU run (wall-clock per loss)

`scripts/premonition_steals_muon_bench.py`: tiny D (d = 32), far-fact toy, 60 steps, 2 seeds, 1 thread, the same
batches. Losses are 5-step window means. "Equal clock" is interpolated at fractions of the shortest arm's seconds.

| seed | arm | final loss | train s | opt step ms | loss @50% clock | @100% clock |
|---|---|---|---|---|---|---|
| 0 | AdamW 3e-3 | 4.986 | 30.9 | 3.5 | 6.01 | 5.00 |
| 0 | Muon 3e-3 (recipe: same lr) | 5.464 | 30.3 | 7.6 | 6.72 | 5.46 |
| 0 | Muon 2e-2 | 4.765 | 35.4 | 8.6 | 5.05 | 4.74 |
| 1 | AdamW 3e-3 | 4.996 | 36.0 | 4.3 | 6.17 | 5.59 |
| 1 | Muon 3e-3 | 5.397 | 35.6 | 8.9 | 6.98 | 5.88 |
| 1 | Muon 2e-2 | 4.691 | 29.7 | 7.5 | 5.00 | 4.69 |

At d = 128 (2.10M parameters, CPU), the Muon optimizer step takes 46 ms against 7 ms for AdamW, which is about 8% of
a 0.49 s training step.

**Reading, suggested:**
- At the recipe lr, Muon is behind AdamW at equal clock in both seeds (+5% to +13% loss).
- At lr 2e-2 it is ahead at equal clock in both seeds (−5% to −19%, the gap shrinking over the run).
- The evidence is 60 steps, 2 seeds and d = 32, on a busy 4-core box where totals swing by about 20%. So it decides
  nothing, but it does say **the lr choice decides the sign**. Run card R1 therefore registers both lrs.

## 5. Recommended A/B order

**Principle.** Stage 0 of every line is the far-fact toy on CPU, which costs $0. Lines run in this order, one change
per run, each against an all-off control with paired seeds (§1 paired init).
- "Decisive" here means aimed at the known blocker. Answers are at chance **even with the gold cards handed in**
  (F2), while retrieval already reaches recall@4 0.90.
- So the training procedure and the answer path come first, and retrieval-side steals wait until answers leave
  chance.
- These bars apply to every line, in house form, all proposed and to be confirmed by the coordinator:
  - paired difference d_s per seed
  - mean(d) − 2·SD(d)/√n > 0 (2× the run's own paired noise, the NOISE.md rule)
  - mean(d) ≥ 3 points (`MIN_EFFECT`)
  - d_s > 0 in at least 2 of 3 seeds (the family rule)
  - non-inferiority bound −3 points (spec §9.4)

| Order | Run | Why here | Stage-0 cost |
|---|---|---|---|
| 1 | **R1: Muon** (optimizer only) | The model is bit-identical, so there is no architecture confound. It decides whether D's chance-level answers are an optimisation problem, which would change how every later run is read. The readout is native wall-clock-per-loss. | $0, ≈ 70 min CPU |
| 2 | **R2: `fetch_gate`** | +0.08% parameters, cost inside the noise. It acts on the card → think → decoder path that the 09-18 handoff names as the blocker ("the decoder never learns to attend to the card"). | $0, ≈ 45 min CPU |
| 3 | `fetch_sink` | +5 parameters. With 3 of 4 fetched cards wrong, decoder heads need a way to attend to nothing. | $0 |
| 4 | `delta_bind` | **Removes** 60,903 parameters. It changes what entity slots carry from cards (the copy path for answers). Being cheaper makes a tie a win. | $0 |
| 5 | `loop_attnres` | +1,024 parameters. Aimed at "Think is the bottleneck" (09-18 handoff, row 11). | $0 |
| 6 | `random_depth`, then `row_halt` | random_depth cuts own-mode training cost by about a third. Read it as non-inferiority plus cost (it is a win if not worse). row_halt only after loop counts mean something (today halt_rate is 0). | $0 |
| 7 | `key_split` | The first retrieval-side run, and only once an answer-path arm leaves chance. §3 says the fix has to be new key information, and position is exactly that. | $0 |
| 8 | `qk_norm`, `qk_clip` | Cheap, but §3 found no magnitude problem for them to fix. Expected null. | $0 |
| 9 | `qk_norm_all` | +23% CPU step time, and no evidence of a problem it fixes. | $0 |
| 10 | `engram` | Only after the F5 ruling, with a name-disjoint held-out split. +8% parameters, so it also needs a size-matched reading. | $0 |
| 11 | `ask_reuse` | No compute to save at this size (F4). I recommend dropping it unless a reason to want staler fetches comes up. | — |

---

## RUN CARD R1: Muon against AdamW (training procedure only)

**Status: DRAFT, UNSEALED, UNFUNDED.** Seal it (`shasum -a 256`) only after the coordinator fills the
**[COORDINATOR]** blanks.

1. **Question.** On the same model, does the Muon option reach a lower held-out loss **per second of training** than
   AdamW, without losing held-out accuracy?
2. **Arms** (each differs from A0 in one thing, the optimizer with its lr):
   - A0: AdamW, lr 3e-3 (`train_toy` default).
   - A1: Muon at the recipe lr, 3e-3.
   - A2: Muon at lr 2e-2.

   **[COORDINATOR] Confirm that both Muon arms are registered.** The smoke run (§4) says the lr decides the sign,
   so registering only one would be a guess. Each arm is read against A0 on its own bar.
3. **Setup.**
   - `train_toy("D", steps=1500, seed=s, optimizer=...)`, tiny preset, the same batches, seeds s ∈ {0, 1, 2}.
   - The model is bit-identical across arms at each seed. The optimizer is the only change.
   - CPU, `OMP_NUM_THREADS=1`, on an **otherwise idle** machine. Arms are interleaved within each seed (A0, A1, A2,
     A0, ...) so that drift in machine speed hits every arm. Step time is logged.
4. **Primary readout.** Held-out loss: teacher mode with the loop count fixed, on 4 fixed held-out toy batches,
   evaluated every 50 steps under `no_grad`, with evaluation time excluded from the clock.
   - The primary value is the held-out loss interpolated at T\* = the shorter arm's total training seconds.
   - The equal-step final loss is reported, not claimed.
   - d_s = loss(A0, T\*) − loss(Ak, T\*).
   - The held-out evaluation hook is a small addition to the bench script, written at $0 after gating.
5. **Bar.**
   - mean(d) − 2·SD(d)/√3 > 0, **and** d_s > 0 in at least 2 of 3 seeds, **and** mean(d) ≥ 3% of A0's loss.
   - **[COORDINATOR]** `MIN_EFFECT` is 3 accuracy points. I propose 3% relative for a loss readout.
6. **Guard.** Ak's held-out toy accuracy (`validate`, own retrieval) must not be more than 3 points below A0's in 2
   of 3 seeds. A loss gain that costs accuracy does not count.
7. **Verdicts.**
   - **PASS:** the bar and the guard both hold.
   - **NOT SHOWN:** the bar fails.
   - **PROVED WRONG:** mean(d) + 2·SD(d)/√3 < 0.
   - **DID NOT TRAIN:** a non-finite loss.
8. **Required rows** (per seed and arm): steps, seconds, ms per optimizer step, s per training step, the held-out
   loss curve, loss at T\*, final losses (lm, ask, ans, halt), accuracy, accuracy with gold cards, recall@4.
9. **What would prove it wrong.** A1 and A2 both behind A0 at T\* by more than 2 SE. That would mean Muon's step
   cost and its lr sensitivity outweigh its per-step gain on D.
10. **Prediction (a guess):** A2 passes on the toy, and A1 is NOT SHOWN or PROVED WRONG.
11. **Stage 1, the GPU village run.** It needs a bid under the Oct 17 rule.
    - Stage 1a: a timing smoke of 300 steps per arm on village data, to measure Muon's step overhead on the GPU
      (cap $0.30).
    - Stage 1b: 3 seed pairs at equal wall-clock (cap $2.50).
    - The prices and estimates are PR 79's: D's s/FLOP has never been measured on a GPU.
    - **[COORDINATOR]** the parent or fresh start, the primary village score, and this week's spend so far.

## RUN CARD R2: `fetch_gate` (gated fetch on card values and decoder cross-attention)

**Status: DRAFT, UNSEALED, UNFUNDED.** Seal it after the **[COORDINATOR]** blanks are filled.

1. **Question.** Does a per-head sigmoid gate on fetched card values and on the decoder's cross-attention move D's
   toy answers off chance, through the cards?
2. **Arms.**
   - A0: `MiniConfig` with every flag off.
   - A1: the same config with `fetch_gate=True` (`config_overrides={"fetch_gate": True}`).

   At each seed, every shared weight and the RNG stream are identical between arms (tested, §1). +1,544 parameters,
   with step cost inside the noise.
3. **Setup.** `train_toy("D", steps=1500, seed=s)`, AdamW (the R1 result does not change this card), seeds
   {0, 1, 2}. CPU, about 7–8 min per run. Precommitted extension rule: if the result sits within 1 SE of the bar,
   add seeds 3 and 4 once, then stop.
4. **Primary readout.** Held-out toy answer accuracy with own retrieval (`validate` → `accuracy`). Chance is 6.25%,
   and A0 was 7.4% in §3. d_s = acc(A1, s) − acc(A0, s).
5. **Bar.** mean(d) − 2·SD(d)/√n > 0, **and** mean(d) ≥ 3 points, **and** d_s > 0 in at least 2 of 3 seeds.
6. **Guards** (a gain counts only through the cards):
   - **G1:** A1's accuracy with the gold cards handed in (`accuracy_gold_cards`) must rise by at least as much as
     its own-retrieval accuracy.
   - **G2:** A1's recall@4 must not fall more than 20% (relative) below A0's.
   - **G3:** the mean card-gate value on gold card rows is reported. If it is below 0.2, the gate has shut the cards
     out, and the gain is "not through cards" whatever the score.
7. **Verdicts:**
   - **PASS:** the bar, G1 and G2 all hold.
   - **"gain not counted (bypassed the cards)":** the bar passes but G1 or G3 trips.
   - **NOT SHOWN / PROVED WRONG / DID NOT TRAIN:** as in R1.
8. **Required rows** (per seed and arm):
   - steps, seconds
   - final losses
   - accuracy, accuracy with gold cards, recall@4, asked_rate, loops, halt_rate
   - mean gate per head: card gate on gold rows, card gate on wrong rows, decoder cross-attention gate
   - d_s
9. **What would prove it wrong.** mean(d) + 2·SD(d)/√n < 0, or both arms at chance (|d| < 1 point in every seed).
   The second would mean gating is not what stops the decoder using cards.
10. **Prediction (a guess):** NOT SHOWN, with both arms near chance. I rank it second because it is nearly free and
    aimed at the right place, not because I expect it to pass. P(PASS) ≈ 0.25.
11. **Stage 1.** Only if stage 0 passes: the PR 79 bid structure (a timing smoke with cap $0.30, then 3 pairs at
    budget F with cap $2.50). **[COORDINATOR]** the parent, the village score and the DEV-slip rule (as in PR 79).

## 6. What I need from the coordinator

1. A code review of `premonition/model.py`, `store.py`, `config.py`, `train.py` and the new `muon.py`. That includes
   the `premonition/` override (F6) and the merge order against PRs 79 and 82 (F7).
2. A ruling on Engram's name-keyed memory (F5).
3. The [COORDINATOR] blanks in R1 and R2, then a yes or no on their stage 0 ($0 CPU).
