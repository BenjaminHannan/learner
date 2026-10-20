# Eight frontier steals in Premonition-mini: build spec (2026-10-17)

The commission is Ben's (Oct 17): implement all eight steals from the coordinator's frontier-research shortlist in the
main model, `premonition/model.py` (D). Everything is a draft until the coordinator has reviewed the code.

## Rules for every steal
- **One flag per mechanism, default off.** The flags already exist in `MiniConfig` (`premonition/config.py`, block
  "Frontier steals"), with their validation and the **exact** parameter count in `parameter_breakdown`. Build modules
  whose parameter counts match that function. `tests/test_premonition_steals_identity.py::EachFlagRunsTest` checks the
  counts, and checks that every flag runs alone and with all the others.
- **Flags off means bit-identical to 73b8e0224.** `AllOffIsBitIdenticalTest` checks init, the RNG stream after
  construction, the three training modes, gradients, `answer()` with each wipe, `answer_with_gold` and trainer
  steps, all with `torch.equal`. Keep it passing:
  - Create new modules and parameters only when their flag is on.
  - Put special inits (open gate bias, ones for gains, zeros for pseudo-queries, sinks) in `reset_parameters`,
    after the existing loops and under the flag. The generic loop already re-inits every `nn.Linear` (weights
    N(0, 0.02), zero bias) and every non-token `nn.Embedding`.
  - Do not reorder or rewrite expressions on the off path. Add `if config.flag:` branches.
- **Signatures are fixed** because subclasses and scripts call them:
  - `_start(batch, hidden, store, mentions)`
  - `_insert(episode, store, index, cards)`
  - `_step(episode, index, step, store) -> (rows, halt, ask, scores)`
  - `_decode_logits(rows, valid, inputs)`, `Decoder.forward(x, memory, valid)`
  - `CardStore.gather -> (values, ents, lines)`
  - `forward(batch, mode, p_own, loops, weights, generator)`. New keyword arguments are fine if they have defaults.
- **Seams** (all neutral when off):
  - `_loop_input`, `_loop_output`, `_ask_scores`, `_choose` (the model's own fetch, used by `answer()`, own-mode
    training and `train.answer_with_gold`)
  - `CardWriter._keys`, `CardWriter._values`
  - `_Episode` fields: `history`, `keep`, `ponder`, `halted`, `ask_cache`, `ask_query`,
    `ask_age`
- Keep fp32 where the code is already fp32 (scores and gates go through `.float()`), so bf16 autocast still works.
- **No training** beyond tiny CPU smoke tests (a few minutes, tiny preset). No GPU.
- **Out of scope:** MoE, full MLA or DSA, wholesale linear attention, speculative decoding.
- **Tests:** one test file per steal, `tests/test_premonition_steal_<name>.py`, in the style of
  `tests/test_premonition_model.py`. Use its `synthetic_batch` and `tiny_config` helpers. Run tests with
  `OMP_NUM_THREADS=1 python3 -B -m unittest tests.<module>`.

Notation: d = d_model, dk = key_dim, H = n_heads, dh = d / H, R = registers.
- Think rows: question (40) | entity slots (16) | card rows (16) | registers (R).
- Register 0 drives ASK and HALT.
- Each ASK score over the L + 1 cards (NULL last) is s = kappa * cos(q, k) + age bias. The query and the keys are
  **already unit-normalised** (`CardStore.write`, `CardStore.ask`).

## 1. `delta_bind`: delta-rule erase-then-write bind (Gated DeltaNet, KDA)
- **Today:** `Think.bind` computes s <- s + sigmoid(g) * (tanh(c) - s), with [g, c] = W_b [s; v]. That is already a
  gated delta rule with the identity as readback: each write replaces a gated share of the **whole** slot. So a
  second card about the same person overwrites the first.
- **Steal (minimal bind form):** read the slot as a matrix S = s.view(a, b), with a = `delta_bind_rows` and
  b = d / a.
  - The card key addresses one direction of it: kappa = normalize(W_a k_card), with
    `think.delta_address = Linear(dk, a)`.
  - [beta, w] = `think.delta_write`([s; v]), with `delta_write = Linear(2d, b + 1)`. Then w = tanh(w) and
    beta = sigmoid(beta), a scalar.
  - Update: S <- S + beta * kappa (w - kappa^T S)^T. The write stores the correction w - readback(S, kappa), and
    the directions orthogonal to kappa stay untouched.
- **Parameters:** with the flag on, `think.binder` is not built (`binder = None`), and `delta_address` and
  `delta_write` replace it. The no-pointers check in `_insert` must now be "neither binder nor delta".
- **Card keys at bind time:** add `CardStore.gather_keys(index, q_visit) -> [n, K, dk]` (unit keys, the NULL key
  for NULL and padding). Bind order stays as today (cards in order, and repeated entities within a card skipped).
- **Tests:**
  - A slot that already reads back w along kappa is unchanged by a second identical write.
  - Two writes with orthogonal addresses both read back.
  - A forward and backward pass gives gradients to `delta_*`.

## 2. `fetch_gate` and `fetch_sink`: gated fetch and per-head sinks (Qwen gated attention, gpt-oss sink)
- **`fetch_gate`, card rows:**
  - `think.fetch_gate = Linear(2d, H)` on [normed register 0 of the asking question (the current `episode.x`);
    card value].
  - Gate = sigmoid(logits) per head, broadcast over that head's dh channels. Bias init is `fetch_gate_bias` (open).
  - The gated value is used for both the inserted card row and the slot bind. NULL cards are gated too.
- **`fetch_gate`, decoder:**
  - `decoder.cross_gate = Linear(d, H)` on `norm2(x)` (query side).
  - It is a headwise sigmoid on the cross-attention output before `cross_proj`. Bias init is `fetch_gate_bias`.
- **`fetch_sink`, decoder:** `decoder.cross_sink = Parameter(H)`, init `sink_init`. It is one extra key per head
  with logit b_h and value 0 in the cross-attention softmax, so a head can attend to nothing. Implement it with
  SDPA by appending a zero key and value and passing a float mask of shape [n, H, len, rows + 1] that is -inf
  where invalid and b_h on the sink column (the q.0 term is 0).
- **`fetch_sink`, ASK:** `heads.ask_sink = Parameter(scalar)`, init `-2 kappa_init` (every score is at least -kappa_init at init), so it starts as a no-op. It is
  appended to the ASK score vector in the set cross-entropy denominator.
  - Questions with nothing left to fetch (the `asks == False` rows) get the sink as their set-CE target, so the
    sink learns "nothing worth fetching". Without that target the loss only pushes the sink down.
  - In `_choose`, a card whose score is at or below the sink is not fetched (-1).
  - ASK has one head today, so "per head" reduces to one scalar in ASK. The NULL card stays, as both a target and
    a fetchable outcome.
- **Tests:**
  - Gate open at init (≈ 0.95).
  - Cross-attention with a sink of -inf equals no sink.
  - A large sink sends cross-attention output to 0.
  - The ASK sink blocks low-scoring cards in `_choose`.
  - The ASK set-CE with the sink equals a hand computation.

## 3. `loop_attnres`: attention residuals across loops (Kimi AttnRes)
- `think.loop_query = Parameter(max_loops, d)`, zero init. This follows Kimi, and means a uniform mix at init.
- `episode.history` holds the register states entering each loop: a list of [Q, R, d] tensors over **all**
  questions (update rows with `index_copy`). v_0 is the initial registers. v_t is the registers after loop t - 1.
- **Mix:** in `_loop_input` at loop t, the registers fed in are sum_i alpha_i v_i over i = 0..t, with
  alpha = softmax_i(loop_query[t] . norm(v_i)). Here `norm` is the parameter-free `_norm`. The mix is done per
  register row and per question. At t = 0 it is the identity.
- Only **registers** are mixed. Card rows are first in, first out and get overwritten by inserts, and slots are
  rewritten by binds, so mixing old copies of those rows would blend evicted cards into new ones. "Register states"
  in the commission is read literally.
- **Tests:**
  - Loop 0 is unchanged.
  - With a zero query, loop t's input registers are the mean of v_0..v_t.
  - Questions that stopped early keep their history.
  - Gradient reaches `loop_query`.

## 4. `engram`: hashed name lookup (Engram)
- **Tables:** `writer.engram_tables = ModuleList(H_e x Embedding(engram_rows, d / H_e))`, with
  H_e = `engram_heads`. Also `writer.engram_key = Linear(d, d)` and `writer.engram_value = Linear(d, d)`.
- **Key:** a line's **names**: for each entity id in `batch.line_ents`, its spelling `batch.names[visit].spelling(e)`
  (an entity without a spelling counts as no name: no fallback key). ENT ids are per-visit variables, so hashing the id would be the same for every person.
  The spelling is the stable identity.
- **Hash:** head h maps a spelling to `int.from_bytes(blake2b(f"{h}:{spelling}", digest_size=8)) % engram_rows`.
  It is deterministic and must never use Python's `hash()`. Cache the indices per spelling.
- **Lookup:** e = mean over the line's names of concat_h(table_h[idx_h]).
- **Engram gate:** alpha = sigmoid(<norm(pooled), norm(W_K e)> / sqrt(d)).
- **Output:** in `_values`, value += alpha * W_V e on lines that have at least one name. Lines without a name get
  nothing added.
- **Parameter cost:** at d = 128 with the defaults it is 131,072 (tables) + 33,024 (W_K, W_V) = 164,096, or +8.2%
  on D. It is reported apart from the 1.9M-2.15M band.
- **Tests:**
  - The hash is deterministic across processes (fixed known indices).
  - The same spelling in two visits gives the same e. Different spellings give different e.
  - A line without names is unchanged.
  - Gradient reaches the tables.

## 5. `row_halt` and `random_depth`: per-register dynamic depth (Mixture-of-Recursions, Geiping recurrent depth)
- **`row_halt`:** `heads.row_halt = Linear(d, 1)`, bias init `row_halt_bias`.
  - In `_loop_output`, for loops t >= 1, p = sigmoid(row_halt(norm(register_in))) per register row.
  - keep_t = keep_{t-1} * [p <= 0.5] in the forward pass, which is sticky, the same in training and on the
    answer paths. Training passes the gradient straight through the soft factor (1 - p) (review round 4: a soft
    forward keep damped training updates that answering never damps).
  - A halted register stops updating: out = in + keep * (think_out - in) on register rows only. It stays a valid
    row, so the other rows still read it.
  - The question-level HALT reads the block's live proposal for register 0, not its frozen stored row (review
    round 5), so a question whose register 0 halted early can still decide to stop.
  - When register 0 is halted (p > 0.5 at some loop, sticky; `episode.halted`), the question stops asking: `_choose` returns -1, and own-mode cards
    are masked.
  - The ponder cost is `row_halt_cost * mean(keep)` over (question, loop, register). It is appended through
    `episode.ponder` and added to L_halt.
  - The question-level HALT (register 0's existing head) is unchanged.
- **`random_depth`:** training samples a cap m ~ U{`random_depth_min`..`max_loops`} per batch.
  - The cap clamps `n_loops` in `forward` (all modes; an explicit `loops=` also gets clamped).
  - Add `forward(..., depth_cap: Optional[int] = None)`. If the flag is on and `depth_cap` is None, forward
    samples m itself from `generator`.
  - `MiniTrainer` samples m from its own generator **before** `batch_cost`, passes it to `planned_loops` (new
    optional argument), and keeps it on `self` for `_train_step`. So FLOP charging matches the loops actually run.
    `_train_step`'s positional signature stays as it is.
  - `answer()` is unaffected.
- **Tests:**
  - A halted register (forced by a large router bias) is frozen while the other rows change.
  - With keep0 = 0 there are no fetches.
  - The ponder term is added.
  - With the cap fixed, `question_loops` equals the clamp.
  - The trainer's planned loops equal the loops run (`loop_mismatches == 0`).

## 6. `qk_norm`, `qk_norm_all`, `qk_clip`, `key_split`: QK-norm, QK-Clip and split keys (Qwen3, Gemma 3, Kimi K2, MLA)
- **Diagnostic first:** `scripts/premonition_steals_qk_diagnostic.py`, on the model with flags off.
  - No trained D checkpoint exists anywhere (survey 10-17). So train the tiny D on the far-fact toy on CPU for a
    few minutes (`train.train_toy`), and report at init too.
  - For each question's own top-k first ASK, split the fetched cards into correct (gold) and wrong. Log:
    - the raw pre-normalisation key norm ||W_k p||
    - the stored key norm (expected 1)
    - the value norm
    - the raw query norm
    - cos, kappa * cos and the age-bias term
  - Report means, medians and counts. Write the results to `artifacts/claude-steals-20261017/qk-diagnostic.json`.
- **`qk_norm` (ASK):** `heads.query_gain` and `heads.key_gain`, both Parameter(dk) with ones init.
  - Score = kappa * <g_q * q_hat, g_k * k_hat> + bias. This is the learned per-dimension metric that QK-norm adds
    on top of the plain normalisation ASK already does.
  - At init it is exactly today's score (test it).
  - The gains are passed to `CardStore.ask` as optional arguments.
- **`qk_norm_all`:** a per-head-dim RMSNorm with a learned weight (`nn.RMSNorm(dh)`, weight ones) on q and k
  before RoPE, in `LocalAttention`, `ThinkLayer`, Decoder self-attention and Decoder cross-attention. Names:
  `q_norm`, `k_norm`, `cross_q_norm`, `cross_k_norm`. That is 2 dh parameters per attention.
- **`qk_clip` (float tau, 0 = off):**
  - In `_ask_scores`, record the largest kappa * cos-part logit over eligible real cards (detached) in
    `self._ask_logit_max`.
  - `model.after_optimizer_step()` is called by `MiniTrainer._train_step` right after `optimizer.step()`, through
    `getattr` so other model classes still work. If the max is > tau, it scales kappa down by tau / max
    (log_kappa += log(tau / max)).
  - Because ASK is already cosine-normalised, kappa is the only logit scale, so this is K2's QK-Clip in full for
    ASK. Clip for other attentions is out of scope (with `qk_norm_all` their logits are bounded anyway).
- **`key_split`:** the last p = `pos_key_dim` dims of every card key and query become a position sub-key. No new
  parameters.
  - The key's last p dims are RoPE-rotated with position = the card's line index (in `CardWriter._keys`). The NULL
    key's last p dims are zero (it has no line), so NULL's score does not depend on the question's line.
  - The query's last p dims are rotated with position = the question's line `q_line` (in `_ask_scores`).
  - Base `key_pos_base`. The first dk - p dims are the content sub-key.
  - After unit normalisation, the dot product's position part depends only on line distance (MLA's decoupled-RoPE
    key, without the rest of MLA). The NULL key's position sub-key is zero.
- **Tests:**
  - With gains of 1, scores equal the base.
  - RMSNorm is applied (q and k rows have RMS 1 times the weight).
  - QK-Clip lowers kappa when the max logit exceeds tau and leaves it alone otherwise.
  - Under `key_split`, shifting every card line and the question line by the same offset leaves the
    position-part dot products unchanged.

## 7. `ask_reuse`: ASK selection reuse across loops (IndexCache)
- Refresh loops are steps where step % `ask_refresh_every` == 0. They also include any loop where the question's
  current unit query has cosine distance > `ask_refresh_cos` from `episode.ask_query` (a threshold of 0 means every loop), and any question with no
  cache yet. Refresh loops score with full matching and store `ask_cache`, `ask_query` and `ask_age = 0`.
- Other loops reuse `ask_cache`, re-masked with the current eligibility: fetched cards become -inf, NULL stays.
  The reused scores keep their graph, and the L_ask terms on reuse loops use them.
- Insertion, gates and binds are recomputed as usual. This is a cache with invalidation, not a frozen fetch: a
  fetched card is never re-fetched, and a moved query forces a rescore.
- **Report honestly:** at D's size, ASK scoring is about 2 dk (L + 1) multiply-adds per (question, loop), against
  about 60M for the think block. So the compute saving is negligible here, and the steal is behavioural only.
- **Tests:**
  - On a reuse loop with an unmoved query, the scores equal the cache minus the fetched cards.
  - With threshold 0 it always refreshes, which is identical to flags off on the same model.
  - Moving the query past the threshold triggers a refresh.

## 8. Muon option (training procedure only; Moonshot Muon report)
- New `premonition/muon.py`:
  - `Muon` for 2-D hidden matrices: Nesterov momentum 0.95, Newton-Schulz with 5 steps and coefficients
    (3.4445, -4.7750, 2.0315) in fp32 on CPU (bf16 on CUDA).
  - Update scaled by 0.2 * sqrt(max(A, B)) so its RMS matches AdamW.
  - Decoupled weight decay at the trainer's `weight_decay`.
  - AdamW for everything else: embeddings (the tied head), norms, biases, gates, sinks, gains, pseudo-queries,
    engram tables, `heads.*`, `think.binder`, `writer.pool` and 1-row matrices.
  - Muon set: Linear weights in `reader.*` (mixers and MLPs), `writer.key` and `writer.value`, `think.layers.*`,
    and `decoder.*` except `cross_gate`.
  - One optimizer object `MuonAdamW` with param groups flagged `muon=True/False`, so the trainer's per-group lr
    schedule and checkpoint state still work.
- `MiniTrainer(..., optimizer="adamw" | "muon")`. The default "adamw" is unchanged. `train_toy(..., optimizer=)`
  passes it through.
- **Benchmark:** `scripts/premonition_steals_muon_bench.py` measures wall-clock per loss on a short tiny-toy CPU run
  against AdamW, with the same seeds and steps. Report loss against seconds and the step-time overhead. Loss per
  step alone is not the claim. Results go to `artifacts/claude-steals-20261017/muon-bench.json`.
- **Tests:** Newton-Schulz output is near-orthogonal; parameter grouping is as listed; a few trainer steps run and
  lower the toy loss; checkpoint state round-trips.
