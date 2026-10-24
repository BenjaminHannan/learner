# Think-1 implementation spec (for the coding agents; the source of truth for marks is PREREG.md)

Repo root: /home/user/learner (branch claude/compassionate-davinci-93ihc5). Write ONLY under backbone/think/.
Do not edit backbone/train.py or any other existing file; import from it instead. Do not commit or push.
Python for tests: /tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/venv/bin/python
(torch 2.14.1 CPU, transformers 5.20.2, peft 0.21.2). Real weights: HF_HOME=/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/hf
with HF_HUB_OFFLINE=1 (Qwen/Qwen3.5-0.8B is cached). Village data (built, digests checked):
/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad/village/{train,dev,validation}.jsonl.
Match the code style of backbone/train.py and backbone/loop/loop1l.py: compact, few comments, plain names.

## Files
1. `backbone/think/xent.py` — fixed cross-entropy (Barron, Gnanapragasam, Tschannen 2026, arXiv 2610.31642).
2. `backbone/think/board.py` — the G-STS module, the cache fork, the gated read patch, think/answer/decode functions.
3. `backbone/think/think1.py` — CLI harness: every arm, training, evaluation, result JSON, `--smoke`.
4. `backbone/think/summarize.py` — reads result files, applies the PREREG marks, prints a report (and `--json`).
5. `backbone/think/test_think1.py` — all CPU tests below; runnable as `python backbone/think/test_think1.py` (no pytest needed;
   pytest-compatible test_* functions are fine too). Fast tests use the tiny random config; `--real` adds the real-0.8B checks.
6. `backbone/think/README.md` — how to run (Ben's PC one-liner, Vast via backbone/vast.py with THINK_JOBS), files, outputs.
7. Update `backbone/think/run_box.sh` so every arm calls think1.py (a and b too, NOT backbone/train.py), with per-arm step
   counts built into think1.py defaults (no global STEPS), and job dependencies: aplus/t/t1/tw need out/think/a_s{S}/adapter,
   bplus needs out/think/b_s{S}/adapter (run a / b first if missing, in the same box).

## 1. xent.py
- `fixed_cross_entropy(logits, target, ignore_index=-100, reduction="sum")`: logits [N,V] (any float dtype; compute in fp32
  internally unless the input is fp64), target [N]. Forward per row: m = -LSE_{j!=t}(z_j - z_t); loss = softplus(-m).
  Custom autograd.Function backward: for j != t, g_j = exp((z_j - z_t) - softplus(-m)); g_t = -sum_{j!=t} g_j (so the row sums to
  zero), times the upstream grad. Rows with target == ignore_index contribute 0 loss and 0 grad. reduction sum/mean/none.
- `fixed_soft_cross_entropy(student_logits, teacher_logits)` and `fixed_kl(student_logits, teacher_logits)` (KL(p_teacher || q_student),
  teacher detached): forward = the standard value; backward from delta = z_S - z_T with p = softmax(z_T):
  d = delta - sum(p*delta); s = d - log1p(sum(p*expm1(d))); u = p*expm1(s); g = u - q*sum(u), q = softmax(z_S). Both losses have the
  same gradient w.r.t. z_S. Reduction over rows: sum (and a mean option).
- Tests (X1-X4): forward equals F.cross_entropy within 1e-6 (fp32) on random logits; at a target margin of 20 (fp32) and 8 (bf16) the
  loss is > 0 or exactly the softplus value, the target gradient is non-zero and every row's gradient sums to 0 within 1e-6 relative;
  with student == teacher, fixed_kl's gradient is exactly 0 in fp32 and bf16 (standard F.kl_div is not, for contrast, printed);
  far from equality, fixed_kl's gradient matches autograd of F.kl_div within 1e-5 (fp64).

## 2. board.py (Qwen3.5 only for now; keep LFM out)
Read before coding: transformers/models/qwen3_5/modeling_qwen3_5.py (Qwen3_5Attention.forward, Qwen3_5GatedDeltaNet.forward,
Qwen3_5DecoderLayer.forward), transformers/cache_utils.py (DynamicLayer.update uses torch.cat and reassigns;
LinearAttentionLayer.update_conv_state / update_recurrent_state write with in-place copy_; Cache.has_previous_state), and
backbone/train.py (Runner.hidden: manual layer loop, mrope position_ids expanded to 3 axes, create_causal_mask /
create_recurrent_attention_mask).

### Cache fork
`fork_cache(C, clone=False)` returns a new Cache object (DynamicCache with the same layer types) whose
- attention layers (DynamicLayer) hold references to C's keys/values (update() cats and reassigns, so C is never mutated);
- linear-attention layers are instances of `AssignLinearLayer(LinearAttentionLayer)` that override update_conv_state and
  update_recurrent_state to ASSIGN new tensors (never copy_), seeded with C's conv/recurrent state tensors by reference
  (clone=False, used by the multi-token slot and answer passes in training/eval) or cloned (clone=True, used for single-token
  greedy decoding, whose fused conv update writes in place). Copy has_previous_state, is_*_initialized, conv_kernel_size, record_past.
- Every slot pass and every answer pass uses its own fork. C must stay bit-identical (test T2). This matters: in HF 5.20.2 a shared
  cache would make lap t+1 read lap t's teacher-forced gold answer.

### Board module `ThinkBoard(nn.Module)`, all parameters fp32
- K=16 (arg), d = hidden_size (1024). rho = median over vocab rows of RMS(embed_tokens.weight) (computed once from the model).
- e0_hat [K,d]: init = embed_tokens rows of 16 distinct tokens of the string " Let me think about where each thing is now and why."
  (take the first 16 distinct token ids; pad with further distinct ids if fewer), divided by rho. e0 = clamp(rho * e0_hat).
- clamp(e): per slot, scale down to RMS rho if its RMS exceeds rho (never scale up).
- eta [d] init 0.1. Refiner: W_in Linear(3*d -> 256, bias); 2 pre-norm blocks (LayerNorm, 4-head self-attention over the K slots of
  each row separately (batch_first=True or a manual implementation; NO mixing across rows), LayerNorm, MLP 256->1024->256 GELU);
  final LayerNorm(256); W_out Linear(256 -> d, default init, with bias). Update: delta = rho * eta * tanh(W_out(norm(u)));
  e_next = clamp(e + delta). Penalty term mean((delta/rho)^2).
- alpha [6 layers, 8 heads] init 0 (one per full-attention layer, per query head). gate = tanh(alpha).
- Taps: input to the refiner = cat(rms(h after layer 11), rms(h after layer 17), final-normed h) at the slot positions
  (layers given by index; for the tiny smoke config with 8 layers use layers 3 and 5).

### Gated read patch
Wrap each full-attention module (Qwen3_5Attention) so that when a board is set (`attn.board = (ks, vs)`, shapes [B, 2 kv heads, K, 256],
the keys/values the slots wrote at this layer in the final slot pass, i.e. post k_norm and post RoPE) and `attn.gate` [8] is given,
the forward adds gate[h] * SDPA(q, repeat_kv(ks), repeat_kv(vs), no mask, same scaling) to the normal attention output for every
query position, BEFORE the `* sigmoid(gate_proj_part)` output gate and o_proj. With board None the forward must be numerically
identical to the original (same ops). Collect slot K/V from the fork after a slot pass: fork.layers[i].keys[..., -K:, :].

### Functions
- `prefill(runner, prompts)`: left-pad prompt[:-1] for each row; run through the frozen model with a fresh DynamicCache (no grad);
  return C, the 2-D mask, and per-row position p_i = len(prompt_i) - 1 (position of the held-back last prompt token).
- `slot_pass(runner, e, C, mask, p)`: inputs_embeds = e (cast to model dtype) on fork_cache(C); position_ids = p_i for all K slots of
  row i (expanded to 3 mrope axes); attention mask = cat(mask, ones(B, K)); causal among slots (HF builds causality from cache index).
  Returns taps (for the refiner) and the slot K/V per full-attention layer.
- `think(board, runner, C, mask, p, L, keep=set_of_L, swap=None, repeat_delta1=False)`: pass 0 on e0, refine, pass 1, ... up to L;
  returns {L: slot_kv} for every L in keep, plus per-lap stats (||e_t - e_{t-1}||/rho, clamp fraction, pairwise slot cosine).
  repeat_delta1: delta_0 (the refiner update after pass 0) is reused: e_{t+1} = clamp(e_t + delta_0) for t = 1..L-1, then one pass on
  e_L for its K/V (2 backbone passes instead of L+1).
- `answer_ce(runner, board, C, mask, p, last_tok, ans, slot_kv)`: answer pass on its own fork: inputs [last_tok] + ans[:-1] at positions
  p_i, p_i+1, ...; right-pad answers across rows (mask them); gated read with slot_kv active; returns summed fixed CE over real answer
  tokens and the count. Logits only at real answer positions.
- `decode(runner, board, C, mask, p, last_tok, slot_kv, max_new=24, eos)`: greedy, cached, on fork_cache(C, clone=True), board read
  active at every step; returns generated id lists. With slot_kv None (or gates forced 0) it must reproduce arm a's greedy output.
- Training loss for one micro-batch: with L_max sampled per optimizer step (8 w.p. 0.8, else 12; t1 and tw: 1):
  mean over t = 0..L_max of answer_ce(board_t)/n_tokens + 0.01 * mean penalty. Backprop through all laps.

## 3. think1.py
CLI: `--arm {a,b,aplus,bplus,t,t1,tw} --seed S --data DIR --out DIR [--model Qwen/Qwen3.5-0.8B] [--max-len 2048] [--bsz 16]
[--micro-bsz 4] [--smoke] [--limit-eval N] [--eval-bsz 64] [--eval-tokens 32768] [--no-cache]`, plus `--a-adapter DIR`
(aplus/t/t1/tw; default out/think/a_s{S}/adapter) and `--b-adapter DIR` (bplus). Reuse backbone/train.py: read_jsonl, normalise,
Encoder, Runner, greedy, left_pad/right_pad, cosine_lr, load_model, LORA_TARGETS, ByteTok, block_order (import it by path).
- Steps (defaults, not flags to change in the prereg run): stage 1 (a, b) 418; stage 2 (aplus, bplus, t, t1, tw) 1,254. Batch 16,
  micro 4. Stage 1: LoRA r16 alpha 32 on LORA_TARGETS, lr 2e-4, cosine, warmup min(100, steps//10), AdamW betas (0.9, 0.999),
  wd 0, clip 1.0, rows from random.Random(seed) shuffled exactly as train.py does. b: Runner(loops=3, start default 8).
- Stage 2 rows: random.Random(seed + 1000) shuffle, same order for aplus, bplus, t, t1, tw. aplus/bplus: load the stage-1 adapter
  with is_trainable=True, re-warm lr to 2e-4 with 60 warmup steps, cosine over 1,254 steps. t/t1/tw: load the a adapter, freeze ALL
  backbone and LoRA weights, train only the ThinkBoard; lr groups: alpha 3e-3, e0_hat and eta 5e-4, refiner 5e-4; warmup 60; cosine;
  clip 1.0 PER GROUP; AdamW wd 0. tw = t1 with K=144.
- Loss for a/b/aplus/bplus: answer CE with xent.fixed_cross_entropy in fp32 (same selection of positions as train.py's
  answer_loss_sum). Training dtype bf16 on CUDA, fp32 on CPU (as train.py).
- Mechanics gate (t/t1/tw): abort (write result with "aborted": reason, exit code 3) if at step 150 mean |tanh alpha| < 0.02, or at
  any step after 20 a NaN loss/gradient or a 20-step mean loss > 2 x the first-20-step mean. Logged every 10 steps but NOT aborts:
  cross-question cosine of the final boards and of their updates (e_L - e_0), share of slots at the clamp (amended 2026-10-24: both
  sit at ~0.99 / ~94% at step 0 on the real model, so they cannot be abort rules).
- Memory: wrap every slot pass in torch.utils.checkpoint (use_reentrant=False) during training by default (flag --no-lap-ckpt to
  turn it off); the prompt cache is never mutated, so recomputation is exact. clamp_rms takes an eps inside the sqrt.
- Logging every 250 steps (t/t1/tw) on the first 256 dev rows: answer CE and greedy accuracy at L = 1 and 8, swap-lesion accuracy at 8,
  |tanh alpha| per layer, refiner grad norm.
- Evaluation (greedy, <= 24 tokens, exact match after normalise, rows sorted by length into batches by eval_tokens):
  validation always all 8,675 rows (unless --limit-eval). Hits are stored as a string of '0'/'1' in FILE ORDER.
  a: dev "main", validation "main"; for seed 0 also validation "main_repeat" (same checkpoint, batches built in reverse length order).
  b: "main" (3 loops) and "pass1" (1 loop) on dev and validation. aplus/bplus: "main".
  t: validation L0, L1, L2, L4, L8, L12 (all rows), L16 and L24 (first 2,000 rows in file order), swap8, mean8, rep1_8, gatesoff8;
  dev L0, L1, L8. Each batch is prefilled once; think() runs to the largest L needed and records slot K/V at every L in the set;
  every L is decoded on its own clone. swap: row i reads the board of another row in the same batch from a different story
  (different `visit_id`; if a batch has only one story, borrow from the previous batch); mean: slot K/V averaged over the batch rows.
  t1: validation L0, L1, L8; dev L1. tw: validation L1.
- Result file `OUT/result_{arm}_s{seed}.json` (and write the adapter / `think_block.pt` into OUT):
  {"arm", "seed", "model", "steps_stage1", "steps_stage2", "k_slots", "params_trainable", "train": {"loss_curve": [[step, loss]...],
   "seconds", "gate_log": [...], "dev_log": [...]}, "aborted": null or reason,
   "eval": {"validation": {TAG: {"acc": float 0-1, "n": int, "hits": "0101...", "row_offset": 0}}, "dev": {TAG: {...}}},
   "label_nums": {short keys: percent floats}}
  by_depth / by_bank / by_qtype are NOT stored; summarize.py recomputes them from hits and the data files.
- `--smoke`: tiny random qwen3_5 config exactly like train.py --smoke (8 layers, 2 full-attention layers at 3 and 7, ByteTok),
  20 rows of each split (from --data if present, else synthetic rows), 6 steps per stage, all arms in sequence into OUT/smoke/,
  then run summarize on them. Must finish in under ~5 minutes on 4 CPU cores.

## 4. summarize.py
`python backbone/think/summarize.py OUT/think [--data DIR] [--json]`: loads every result_*.json, the validation/dev rows (for depth,
bank (the `bank` field), qtype, visit_id) and prints: per arm and seed the main numbers; the t lap curve; lesions; then each PREREG mark
with its numbers and PASS / FAIL / not-enough-data: G, R1, R2 (tol = max(0.3, 2 x |a s0 main - main_repeat| in points)), R3, R4,
the four wrong-if rules, the futility rules (seed 0 only), M1 (bank in {q.where_before, q.plan_get}), M2 (depth >= 4), and the final
verdict (PASS / WRONG / PARTIAL / FUTILE-STOP / INCOMPLETE). Floors: A_ref = max(66.72, mean a, mean aplus), B_ref = max(67.12,
mean b, mean bplus if present). All differences that compare arms on the same rows are paired; give a paired bootstrap 95% interval
(2,000 resamples, fixed seed) for S(8) - T1, S(8) - S(1) and S(8) - max(A, B). Accuracies are reported in percent with 2 decimals.
Test (S1) with synthetic result files built in the test: a PASS case, a WRONG case (laps add nothing), a FUTILE case (seed 0 only).

## 5. Tests (test_think1.py) — all must pass on CPU before any GPU run
T1 alpha = 0: answer logits from the board path equal stock arm-A logits (Runner.hidden on the full sequence) to max |diff| <= 1e-5
   (fp32) at L = 0, 1, 4, 8 — tiny config and (--real) the real 0.8B on 3 short validation rows.
T2 After think() to L=8 and 9 answer passes, every tensor in C is torch.equal to a deep snapshot taken before.
T3 Slot hidden states from a fork pass equal a no-cache forward of [embed(prompt[:-1]); e] with the same position ids, to 1e-4.
T4 Cached greedy decode with a board (alpha != 0) equals a no-cache reference decode (full re-forward each step with the read branch)
   at L = 1, 4, 8.
T5 With alpha set to 0.5: after one backward, every ThinkBoard parameter has a non-zero grad, and no backbone or LoRA parameter has
   any grad. A float64 gradcheck on a very small config passes through one fork and one lap (or a finite-difference check on 5 params).
T6 A row's answer logits alone equal its logits inside a left-padded batch of 3 different-length rows, to 1e-4.
T7 alpha = 0: the swap lesion leaves logits unchanged; alpha != 0: it changes them.
T8 Same seed: identical stage-2 losses over 10 steps (CPU).
T9 No leak: changing the answer tokens leaves the lap-(t+1) board (e_{t+1} and its slot K/V) unchanged.
T10 Batch permutation: permuting the rows of a batch permutes the boards and logits the same way (no cross-row mixing).
X1-X4 xent tests above. S1 summarize test above.
SM `think1.py --smoke` runs all arms end to end and summarize prints a verdict line.

## Round 2 additions (2026-10-24, after the first build; all must be in before any GPU run)
1. `--dtype {bf16,fp16,fp32}` for think1.py (default: bf16 on CUDA, fp32 on CPU). fp16 is for Kaggle T4s (no bf16): backbone
   weights in fp16; every trainable parameter (LoRA, ThinkBoard) kept in fp32; forward under torch.autocast("cuda", float16);
   torch.cuda.amp.GradScaler (or torch.amp.GradScaler("cuda")) around backward/step, unscale before the per-group clipping;
   skip-and-log steps whose grads are inf/nan (count them in the result; the divergence guard ignores scaler-skipped steps).
   Loss/CE always fp32 (xent already casts). Record dtype, GPU name and torch/transformers versions in the result file.
   Evaluation runs in the same dtype as training. bf16 requested on a GPU without bf16 support must exit with a clear message.
2. Lap gradient checkpointing (default on in training, `--no-lap-ckpt` to disable) and an eps in clamp_rms (see the gate section).
3. Mechanics gate as amended above (only gates-shut at step 150, NaN, divergence abort; cosine and clamp share are logs).
4. run_box.sh: `PARALLEL=1` runs the stage-2 jobs of the job list (aplus, bplus, t, t1, tw) as concurrent processes on the same GPU
   once their stage-1 adapters exist (stage-1 jobs a and b also run concurrently with each other when both are listed), each with
   its own log file out/think/{arm}_s{S}/run.log, and waits for all; `WAIT_DEPS=1` makes a job whose stage-1 adapter is missing
   wait (poll every 60 s, give up after `WAIT_DEPS_HOURS`, default 6) instead of training it, so two Kaggle lanes can share one
   a-adapter through the shared disk. `DTYPE` env passes `--dtype`. Keep the existing sequential behaviour as the default.
5. README: add the Kaggle recipe (tools/kaggle_job.py from branch claude/project-thread-ustqtb, 2x T4, lane0 / lane1 job lists,
   DTYPE=fp16, WAIT_DEPS=1), the Vast recipe (backbone/vast.py pack --slim --env "THINK_JOBS=... PARALLEL=1"), and Ben's PC
   one-liner (seed 2: THINK_JOBS=a:2,b:2,aplus:2,t:2,t1:2 PARALLEL=1 bash backbone/think/run_box.sh), with expected outputs.
