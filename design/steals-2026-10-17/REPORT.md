# Eight frontier steals in Premonition-mini: implementation report

Written 2026-10-17 (UTC); revised 2026-10-18 after the Q39 code review and the coordinator's rulings Q39–Q43.
**Status: DRAFT.** The code review (§7) came back PASS WITH FIXES. The fixes are applied and re-verified here; the
coordinator decides whether that clears Q39. No training beyond tiny CPU smoke runs, no GPU, nothing booked.
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
| F5 | Engram is a neutral capacity add | Hashing **name spellings** gives D a parametric memory of specific names. The project's design keeps facts in the notebook and starts it empty, and village names repeat across worlds. | **Ruled (Q40): HOLD.** No Engram A/B on any split whose train and held-out names overlap. The only permitted form is a name-disjoint held-out split plus a size-matched reading of its +164,096 parameters, under the §5 bars. It stays last. |
| F6 | editing `premonition/` is fine | `handoff/HANDOFF.md:33` forbids edits under `premonition/`. | **Override confirmed (Q39):** this was Ben's own commission. The review checked the diff stays inside the steals' scope (§7). |
| F7 | this lands alone | PR 79 (`decoder_reader_kv`) and PR 82 (span cards) edit `model.py` and `config.py` from the same base. | **Ruled (Q41):** nothing merges yet. Branches land one at a time, in the order their reviews pass. A later branch rebases onto the new `main`, re-runs its identity harness against that new base, and resolves the conflicts itself. |

## 1. Summary per mechanism

D = 2,013,140 parameters at d = 128 with the v1 vocabulary. The cost columns come from
`scripts/premonition_steals_costs.py`: 4 synthetic visits × 40 lines, CPU, 1 thread, median of 7 steps (forward +
backward).
- "FLOPs" is the FlopCounterMode count (matmuls and attention only). Gates, norms and hashing are elementwise, so
  they are not counted.
- These numbers were re-measured on 10-18 on an otherwise idle machine. The first run, on 10-17, overlapped other
  jobs.
- **The time noise floor is about ±4%.** The same all-off model, timed a second time, gives −0.4%, +0.2% and −3.7%.
  Read any step-time change inside ±5% as noise.
- `random_depth` is averaged over every equally likely loop cap (1..8). It is the expected cost, not one sampled
  draw.

| # | Steal | Flag(s) | Params Δ | FLOPs Δ (gold/teacher/own) | CPU step time Δ (gold/teacher/own) | Tests |
|---|---|---|---|---|---|---|
| 1 | Delta-rule erase-then-write bind | `delta_bind` | **−60,903** (the binder is replaced) | −0.04 / −0.06 / −0.03% | −11.8 / +0.9 / −4.0% | 13/13 |
| 2 | Gated fetch | `fetch_gate` | +1,544 | +0.02 / +0.01 / +0.02% | −2.7 / +0.4 / +6.6% | 22/22 (with sinks) |
| 2 | Per-head sink | `fetch_sink` | +5 | ≈ 0 | −2.0 / +4.0 / +4.5% (noise) | (same file) |
| 3 | Attention residuals across loops | `loop_attnres` | +1,024 | 0 | +4.9 / +9.0 / +7.9% | 11/11 |
| 4 | Engram hashed name lookup | `engram` | **+164,096 (+8.15%)** | +0.09 / +0.05 / +0.03% | −6.1 / −3.5 / −1.2% (noise) | 16/16 |
| 5 | Per-register halting | `row_halt` | +129 | ≈ 0 | −5.9 / −1.8 / +0.7% (noise) | 26/26 (with depth) |
| 5 | Random-depth training | `random_depth` | 0 | −4.4 / −15.5 / **−39.6%** | −7.6 / −17.2 / **−38.7%** | (same file) |
| 6 | QK-norm on ASK (gains) | `qk_norm` | +128 | 0 | −3.5 / −3.3 / −7.5% | 21/21 (QK family) |
| 6 | QK-norm on all attention | `qk_norm_all` | +320 | 0 | +5.6 / **+13.6 / +19.8%** | (same file) |
| 6 | QK-Clip on ASK | `qk_clip` (τ, 0 = off) | 0 | 0 | −4.3 / −0.9 / +3.9% (noise) | (same file) |
| 6 | Content + line-position sub-keys | `key_split` | 0 | 0 | −0.6 / +0.4 / +0.9% (noise) | (same file) |
| 7 | ASK-selection reuse | `ask_reuse` | 0 | −0.01% | −8.1 / +2.1 / +5.4% | 9/9 |
| 8 | Muon optimiser | `MiniTrainer(optimizer="muon")` | 0 | 0 | optimizer step 48.8 ms against AdamW's 7.5 ms (6.5×): about +41 ms on a ≈ 0.47–0.51 s step (**+8–9%**, CPU d = 128) | 21/21 |

- **Real costs above the floor:**
  - `random_depth`: −40% expected own-mode cost. The cap clamps own mode's 8 loops to E[cap] = 4.5. Teacher mode
    mostly runs fewer loops than the cap anyway.
  - `qk_norm_all`: +14–20%. On CPU, `RMSNorm` runs unfused.
  - `loop_attnres`: +5–9%, from the per-loop softmax mix.
- **Single outliers:** `delta_bind` at −12% in gold mode and `ask_reuse` at −8% in gold mode sit outside the floor
  in one mode only. I did not investigate them, and they are not claimed.
- **Muon:** the overhead is Newton–Schulz itself. Swapping the AdamW half for torch's own AdamW did not change it on
  CPU (§7).

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
- Since the review, the base side is built by the base commit's own `config.py` as well.
- The test fails on a 1e-7 weight perturbation, so it is not vacuous.
- The independent reviewer ran a separate check. It built the base and branch trees with `git archive`, ran them in
  separate processes and compared about 1,800 tensors. That check covered paths the harness does not: CPU bf16
  autocast, `train_toy`'s calibrate, budget and train loop through every phase, `validate`, a full-size
  forward and backward, and checkpoint save, resume and step. **Everything matched**, apart from the two
  config-level items now fixed (§7).

**Configs and checkpoints, shown.**
- Every config the base accepts is still accepted, including odd-but-valid widths such as d = 36 or 20, which the
  first draft wrongly rejected.
- Each such config counts the same parameters as before.
- Each serialises to the **same checkpoint `config.json` as the base**: steal fields left at their defaults are
  not written. So older code still reads a flags-off checkpoint, and new code reads old ones.

**Composability, shown.** Each flag alone, and all flags together, builds, trains every mode with finite losses and
gradients, answers, and takes trainer steps. The hand parameter count equals the modules' count. The two controls
(D-noask, D-noptr) take every flag.

**Paired init, shown.** Steal modules are built off the global RNG stream (`model._aside`), and they are initialised
by an explicit generator, so no global stream, CPU or CUDA, is touched. So at a given seed, every shared weight and
the RNG state equal the flag-off model's, and a paired A/B differs only in the steal (per single steal: with several steals on, each steal's side-stream weights depend on which others are on,
because they share one side stream in module order; every planned A/B changes one flag). This includes `delta_bind`:
the binder it removes still has its init draws taken (`model._Draws`), so every later weight matches. That is tested
for every flag, variant and seed.

**Suite, shown.** All 103 test files were run one by one on this branch and on an untouched `main` checkout.
- Every pre-existing file has the same outcome on both.
- The 9 new files (152 tests) all pass.
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
  - `_choose` drops cards that score at or below it. It starts at −2κ_init. Every score is at least −κ_init at
    init, so it starts as an exact no-op. (The first draft started it at −κ_init, which could drop a card with
    cos ≈ −1.)
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
- It is a cache with invalidation, not a frozen fetch. A threshold of 0 is defined as "refresh every loop", and the
  result then equals the flag-off model (tested).
  - The first draft tested `1 − cos ≥ 0`. In fp32 that can be false for an unchanged unit query (the reviewer
    measured 22%), so a frozen query could reuse the cache.
  - A regression test now fails under the old rule.
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
  - This half is **torch's own `torch.optim.AdamW`** (fused on CUDA, like the base trainer). R1's wall-clock
    comparison therefore charges Muon only for Muon.
  - The first draft hand-wrote AdamW as a per-parameter Python loop. `MuonAdamW` now presents one interface over
    the two parts.
- `MiniTrainer(optimizer="muon")`, `train_toy(optimizer=)`.
- A Muon checkpoint records its optimizer and resumes as Muon (tested). The default `"adamw"` path is
  bit-identical.
- Fused matrices are orthogonalised as one matrix each: the GRU input (z, h̃ and gate), attention `qkv`, and the
  decoder's `cross_kv`. A split variant is untested.
- QK-Clip runs only through `MiniTrainer._train_step`. A script with its own training loop must call
  `model.after_optimizer_step()` itself.

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

At d = 128 (2.10M parameters, CPU), the Muon optimizer step takes 48.8 ms against 7.5 ms for AdamW, which is about
8–9% of a 0.47–0.51 s training step. This was re-measured on 10-18 with the AdamW half now torch's own AdamW, and it
is unchanged from the first run (46 ms). The equal-clock table above is the 10-17 run; the 10-18 re-run gives the
same signs in both seeds (`muon-bench.json`).

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
| 6 | `random_depth`, then `row_halt` | random_depth cuts expected own-mode training cost by about 40%. Read it as non-inferiority plus cost (it is a win if not worse). row_halt only after loop counts mean something (today halt_rate is 0). | $0 |
| 7 | `key_split` | The first retrieval-side run, and only once an answer-path arm leaves chance. §3 says the fix has to be new key information, and position is exactly that. | $0 |
| 8 | `qk_norm`, `qk_clip` | Cheap, but §3 found no magnitude problem for them to fix. Expected null. | $0 |
| 9 | `qk_norm_all` | +23% CPU step time, and no evidence of a problem it fixes. | $0 |
| 10 | `engram` | Only after the F5 ruling, with a name-disjoint held-out split. +8% parameters, so it also needs a size-matched reading. | $0 |
| 11 | `ask_reuse` | No compute to save at this size (F4). I recommend dropping it unless a reason to want staler fetches comes up. | — |

---

## RUN CARD R1: Muon against AdamW (training procedure only)

**Status: blanks filled by the coordinator (Q42).**
- **Stage 0 is approved:** $0, CPU, seeds 0–2, but only after the Q39 review passes.
- **Stage 1 is not approved.** It gets its own bid, and only if stage 0 passes.
- Spend as of the ruling: $5.58 spent and $29.86 committed of the $50/week cap.

1. **Question.** On the same model, does the Muon option reach a lower held-out loss **per second of training** than
   AdamW, without losing held-out accuracy?
2. **Arms** (each differs from A0 in one thing, the optimizer with its lr):
   - A0: AdamW, lr 3e-3 (`train_toy` default).
   - A1: Muon at the recipe lr, 3e-3.
   - A2: Muon at lr 2e-2.

   **Both Muon arms are registered (Q42).** Each is read against A0 on its own bar.
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
   - `MIN_EFFECT` for this loss readout is **3% relative (confirmed, Q42)**.
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
    - The parent (or fresh start) and the primary village score go in the stage-1 bid. Q42 leaves them unfilled.

## RUN CARD R2: `fetch_gate` (gated fetch on card values and decoder cross-attention)

**Status: blanks filled by the coordinator (Q43).** The bar and guards G1–G3 are confirmed as written.
- **Stage 0 is approved in principle:** $0, CPU, run **second**, after R1's stage 0, and only after the Q39 review
  passes.
- Stage 1 gets its own bid, and only if stage 0 passes.

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
    budget F with cap $2.50). The parent, the village score and the DEV-slip rule go in that bid.

## 6. Rulings received (Q39–Q43, 10-18)

| Ruling | What it says | Where it now stands |
|---|---|---|
| Q39 | Code review on the whole package, with the built-in review plus an independent read. Code stays DRAFT until it passes. The `premonition/` override is confirmed. | §7 |
| Q40 | Engram: HOLD as designed. Only a name-disjoint split with a size-matched reading. | F5, §5 row 10 |
| Q41 | No merges yet. Land in review-pass order, one at a time; later branches rebase and re-run their identity harness against the new base. | F7 |
| Q42 | R1 blanks filled. Stage 0 is yes after Q39. | R1 |
| Q43 | R2 blanks filled. Stage 0 is yes in principle, second, after Q39. | R2 |

## 7. Code review (Q39, 10-18)

**Method.** This follows the owner's rule:
- The Claude Code built-in `/code-review` (high) was run on PR 84.
- An **independent read** ran alongside it: a separate read-only agent that re-derived the bit-identity claim itself
  rather than trusting this report.
- After the fixes, the built-in review was run again on the **whole fixed package** (branch
  `claude/steals-8-fixes` against `main`).
- The independent probe was re-run on the final tree.

**Independent read, verdict PASS WITH FIXES (nothing blocking).**
- It found no off-path difference in the model, card store or trainer.
- Its separate probe matched on every path it tried (§1).
- It confirmed two config-level should-fix items, rows 2 and 3 below.

**Findings and what was done.** Nos. 1–10 are from round 1 of the built-in review, i1–i9 from the independent read,
and r1–r10 from round 2. "Fixed" means fixed with a regression test unless the row says otherwise.

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | Side-stream init called `torch.manual_seed` inside a CPU-only `fork_rng`, so it would reseed the global CUDA RNG | real (GPU paired A/Bs) | **Fixed.** Steal modules are initialised by an explicit `torch.Generator`. Construction forks only the current CUDA device, and only when the default device is CUDA (r2). |
| 2 / i1 | Steal-only config checks ran with flags off and rejected valid configs (d = 36, d = 20); `delta_bind_rows=0` gave a ZeroDivisionError | should-fix, confirmed | **Fixed.** Every check is gated on its flag. A harness test accepts those configs and counts the same parameters as base. |
| i2 | A flags-off checkpoint's `config.json` gained 24 keys, so the base code could not resume it | should-fix, confirmed | **Fixed.** Steal fields are written only when a steal is on, and then all of them (r6). Flags-off `config.json` equals base (tested). |
| 3 / i5 | `budget_for_steps` ignored `random_depth`, so `train_toy(steps=N)` ran about a third more steps | real | **Fixed.** The budget is the mean over caps. A test checks that 40 requested steps run 28–52. |
| 4 / i3 | `ask_refresh_cos = 0` did not guarantee a refresh (fp32 `1 − û·û < 0`) | note, confirmed | **Fixed.** 0 means "every loop" by definition, and the SPEC text is aligned. A regression test fails under the old rule. |
| 6 / i4 | `random_depth` sampled in any grad-enabled forward, and the cost figure came from one draw | real | **Fixed.** It samples only in training mode. The cost script averages over all caps (§1). |
| 8 | Muon's AdamW half was a per-parameter Python loop, which billed extra time to Muon | real (R1 fairness) | **Fixed.** That half is now `torch.optim.AdamW` (fused on CUDA). The Muon bench was re-run (§4). |
| i9 | ASK sink at −κ_init was only roughly a no-op | note | **Fixed.** It starts at −2κ_init, below every score at init. |
| r1 | The R1 runner reused saved arms without checking their settings | real | **Fixed.** Settings are stored with each run, and reuse with other settings is refused. |
| r3, r4 | Report numbers for `random_depth` and the Muon overhead were stale after the fixes | real | **Fixed.** Re-measured on an idle machine (§1, §4). |
| r5 | A pre-fix Muon state gave a bare `KeyError` | minor | **Fixed** with a clear error. No such checkpoint exists outside tests. |
| r7 | `MuonAdamW`'s input check never fired | minor | **Fixed.** Plain parameter lists are accepted again. |
| r8 | The R1 scorer hard-coded 3 seeds | real | **Fixed.** It refuses to score anything but the card's seeds (0, 1, 2). |
| r9 | The R1 runner did not interleave arms within a seed, as the card says | real | **Fixed.** Arms run in round-robin chunks of 50 steps. |
| r10 | The R1 runner copied `train_toy`'s setup | should-fix | **Fixed.** A new `train.toy_setup`, which `train_toy` itself now calls, is shared (same op order; the probe re-verified it). |
| 5 | Query RoPE and QK gains are wrappers that each `store.ask` caller must remember | design note | **Not changed.** Every model path uses them. Probes and scripts that call `store.ask` directly score the old way under `key_split` or `qk_norm`, which this note records. |
| 7 | Engram rebuilds hash indices on the host every forward | performance note | **Not changed.** Engram is on HOLD (Q40). Precomputing indices at batch build goes into any Engram stage-1 bid. |
| 9 | Use the upstream `torch.optim.Muon` | design note | **Not changed.** The local Mac and BensPC torch versions are not pinned to one that has it. The hand version is tested against the recipe. |
| 10 | `hasattr` and `None` conventions are mixed for optional modules | style | **Not changed.** |
| i6 | Fused `qkv` and `cross_kv` are orthogonalised as single matrices | note | **Documented** (§2). |
| i7 | QK-Clip runs only through `MiniTrainer._train_step` | note | **Documented** (§2). |
| i8 | `row_halt` and `loop_attnres` assume the registers are the last rows | note | **Documented.** The subclasses that append rows refuse the think path today. |

**Round 3 (built-in review of `claude/steals-8`, requested by the coordinator; fixes under the coordinator's GO).**
Nos. 1–3 were confirmed by running code before any fix. Items 6 and 10 were already fixed on the fixes branch
(round 1, nos. 6 and 8).

| # | Finding | Disposition |
|---|---|---|
| 1 | The QK-Clip peak was an untracked tensor attribute, so `read_only` evaluation failed after a training forward that no optimizer step followed (confirmed) | **Fixed.** It is a non-persistent buffer, registered only when `qk_clip > 0` and not in `state_dict`. A test runs a `read_only` answer after a training forward. |
| 2 | A forward that never reached ASK left a stale peak, and κ was clipped by it (confirmed) | **Fixed.** Every training forward resets the peak first. A test checks that an empty batch after a high-peak forward leaves κ alone. |
| 3 | `row_halt`: training stopped asking on soft keep < 0.5 while answering used sticky p ≤ 0.5, so the two disagreed (confirmed; p = 0.4 gives 0.36 against 1) | **Fixed.** Both paths stop asking on one sticky indicator, p > 0.5 at some loop (`episode.halted`). The soft keep still blends updates in training. A test at p = 0.4 and p = 0.6 checks both paths and fails under the old rule. |
| 4 | `delta_bind` dropped the binder's RNG draws, so every later weight moved | **Fixed.** `_Draws` takes the removed binder's construction and init draws in its place. The paired-init test now covers every flag with no exception. |
| 5 | Callers outside the model must set `hard` by hand and use the ASK wrappers | Not changed (design note, as round 1 no. 5). |
| 6 | `random_depth` sampled in any grad-enabled forward | Already fixed (round 1, no. 6). |
| 7 | Engram's per-forward host loop and its unbounded cache | Not changed (Engram is on HOLD, as round 1 no. 7). |
| 8 | The sink set-CE copied `set_cross_entropy` | **Fixed.** It now calls it. |
| 9 | `gather_keys` copied `gather`'s indexing | **Fixed.** Both share `CardStore._slots` (`gather` is on the off path, and the probe re-verified it). |
| 10 | Muon's AdamW half was a Python loop | Already fixed (round 1, no. 8). |

**Round 4: re-review of the pushed `claude/steals-8` at 7865a0550. Fixes under the coordinator's GO, round 2, 10-18,
resumed 10-19.**

| # | Finding | Disposition |
|---|---|---|
| 1 | Under `key_split` the query's position part is rotated, but the NULL key went to the store unrotated. NULL's score therefore depended on the question's line: the same query scored +0.157 against NULL at line 3 and +0.246 at line 40 (confirmed). | **Fixed.** NULL has no line, so its position sub-key is zero (`CardWriter._null_key`), and its content part still learns. A test shows NULL's score is the same at lines 3, 17 and 40, and it fails on the pre-fix model. |
| 2 | `row_halt` damped every training update by the soft keep Π(1 − p) (×0.66 by loop 8 at init), while answering applied full updates. Round 3 had aligned only the "stop asking" rule. | **Fixed at the root.** keep is now a straight-through product: its value is the hard sticky 0/1 keep (p > 0.5 once means halted) in training and answering alike, and its gradient is the soft keep's, so the router and the ponder cost still learn. `episode.hard` was only needed for the old split, so it is removed, which also removes the "callers must set hard" hazard of round 3 no. 5. Tests check: the forward value is exactly 0/1 with the soft gradient; the grad and no-grad paths give identical keeps and rows; the p = 0.4 / p = 0.6 test from round 3 still passes. The test fails on the pre-fix model. |
| 4 | Engram: a visit with no `NameTable` used hashed row 0, and a missing spelling fell back to `"<ent e>"`, which gave the same row to id e in every visit. | **Fixed.** An entity without a spelling counts as no name, and a line with no spelled names is unchanged. A test covers empty tables, a missing table and one missing spelling, and it fails on the pre-fix model. |
| 10 | QK-Clip's `amax` raises on a store with zero card lines. | **Not reachable.** Such a store already fails earlier, in the base commit's own `CardStore.ask` (an empty age-bias row, code unchanged since 73b8e0224), so the base model cannot score it either. The `numel` guard is kept as defence. A test shows the flag-on and flag-off models fail identically on that input, so QK-Clip adds no new failure. |

Items 3 and 5–9 of that review are the documentation and efficiency notes that the coordinator ruled should wait.
Item 3's documentation line is in §1: paired init holds per single steal; with two steals on, one steal's side-stream
weights depend on which others are on.

**Re-verification after the round 4 fixes (commit 3537dd429).**
- Every new test fails on the pre-fix model and passes on the fix.
- **Independent probe** (`git archive` trees, separate processes): of 1,853 recorded entries (1,816 tensors), the
  same **6 differ from base, all of them timing fields**.
- **Full suite**, all 103 files one by one: **every pre-existing file has the same outcome as on untouched
  `main`**, and the 9 steal files (152 tests) all pass.

**Scope (both reviewers).**
- Code changes are limited to `premonition/{config,model,store,train}.py` and the new `premonition/muon.py`.
  `learnlab/`, `memorylab/` and `archive/` are untouched.
- Every off-path change is a neutral seam or sits behind a flag, and running them showed they are identical.

**Re-verification after the round 3 fixes (commit 527f2a740).**
- **Identity harness.** `tests/test_premonition_steals_identity.py`, 11 tests, passes. The base side is now built
  by the base commit's own `config.py`. The paired-init test covers every flag.
- **Independent probe.** The reviewer's own probe (`git archive` trees, separate processes) was re-run on the new
  commit. Of 1,853 recorded entries (1,816 tensors), **6 differ from the base, and all 6 are timing fields**
  (seconds, tokens per second). The two config-level differences from round 1 are gone.
- **Full suite.** All 103 test files were run one by one. **Every pre-existing file has the same outcome as on
  untouched `main`**, and the 9 steal files (150 tests) all pass.
- **Built-in review.** It was then run again on the pushed `claude/steals-8`. Its verdict is reported to the
  coordinator in the session, not here, so the report does not pre-judge it.
