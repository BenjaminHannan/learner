# TRM-Text: tiny recursive slot reasoner with a linear talker (trm_text)

_Nothing pretrained. A 2-layer char-conv reader feeds one 2-layer net that is reused many times: it refines 15 hidden scratch slots plus 9 answer slots with TRM-style deep supervision. The answer is a linear readout of the answer slots, which never see the question directly. At 3.1M params and the same FLOPs as plain_tf, it is likely to tie overall and could win on multi-step chains._

## reader

ConvReader (custom, no transformer, nothing pretrained).
- Input: prompt_ids [B,T<=208] and prompt_mask.
- x = char_emb(ids) [108 x d] + learned abs pos_emb [208 x d], with padding masked to 0.
- Then 2 residual pre-LN blocks: x = (x + Conv1d(d,d,k=5,pad=2)(GELU(LN(x)))) * mask. Final LayerNorm gives X [B,T,d] (d=256 at 3M, 480 at 10M).
- Computed once per example. Each reasoner layer then projects X once to cross-attention K,V ([B,h,T,d/h], cached across all recursions).
- Receptive field is 9 chars (by construction).

What it CAN compute:
- Character identity and word shape.
- Digit place value inside a number of up to 4-5 digits (it sees up to 4 chars to the right).
- Local context such as 'away 16' or 'qty 4'.

What it CANNOT compute (by construction):
- It cannot relate two tokens more than 4 chars apart, so it cannot bind a name to a number across clauses, count list items, compare two table entries, or chain operations.
- It has no output path, so it cannot answer anything. Its only consumer is the reasoner's cross-attention.

Unseen dev characters (# @ & $ O) keep their untrained init embeddings, the same as plain_tf.

## reasoner

TRM adapted from grids to text: Perceiver-style slots instead of per-cell states, so the state does not scale with prompt length.

State:
- z [B,15,d]: latent scratch slots.
- y [B,9,d]: answer-draft slots. Slot j holds the j-th answer char counted from the END (LSB-first), then EOS.
- Both start at 0.

One shared net f, 2 layers, post-norm RMSNorm (TRM style, so the state RMS stays 1). Each layer:
- s = RMSNorm(s + SelfAttn(s)) over the 24 slots, 8 heads.
- [think calls only] s = RMSNorm(s + CrossAttn(q=s, K,V=X)) with the prompt key mask.
- s = RMSNorm(s + W2 GELU(W1 s)), MLP d -> 5d -> d.

Input to every call: concat[z;y] + slot_id_emb (24 x d, init std 1, the same scale as the state) + role_emb (think or answer, std 1).
- think call: z <- f(...)[:15]. It reads the prompt again on every call (input injection by cross-attention, as in Recall/TRM). y is unchanged.
- answer call: y <- f(...)[15:] with cross-attention switched off (kv=None). z is unchanged.

Loop structure:
- cycle = n_think (2) think calls + 1 answer call.
- supervision step = t_cycles (2) cycles; the first runs under no_grad and the last with full backprop (6 layer applications).
- z and y are detached between supervision steps.
- n_sup = 2 in training and by default at test. The harness loops:K sets K supervision steps (sweep K = 0,1,2,4).
- All calls share f's weights.
- No halting in v1 (fixed steps). A Q-head is a later add-on.

Effective depth at test: 2 sup x 2 cycles x 3 calls x 2 layers = 24 layer applications, against 4 for plain_tf 3.2M, at equal training FLOPs.

Prototype check (shown, CPU, random init only):
- Initial CE is 4.79 against ln(108) = 4.68.
- Every parameter gets gradient.
- The state changes by 100%, 1.4% and 0.1% across supervision steps 1-3 at init. Not stateless by design, but at random init it settles fast; the trained dynamics are untested.

## talker

The talker is a tied linear readout per answer slot: logits_j = RMSNorm(y_j) . E^T, where E is the reader's 108 x d char embedding (0 extra params). Greedy decoding reads the slots until EOS or PAD, then reverses the string.

Confirmed: the talker sees ONLY the reasoner's final answer slots y. It does not see z, the prompt, X, or the other slots. y itself is written only by answer calls, and those have no cross-attention to the prompt. So the only path from question to answer is: reader -> think calls' cross-attention -> z -> answer call -> y -> linear head.

A per-slot linear map cannot combine information. This meets Ben's design note: the talker translates the state and does no reasoning (by construction).

Harness split (base.py state/talk contract, commit 3f2be3c6a):
- state(batch, loops) returns y.
- talk(y, batch) is the linear readout. It uses nothing from batch.
- So the donor-swap and shuffle_state lesions work as they are.

## why_reasoner_must_reason

Bottleneck argument (by construction):
- (1) The reader is local (9-char receptive field) and has no output path.
- (2) The talker is a per-slot linear map from y.
- (3) y is updated only from [z;y] with the prompt masked out.
- So every non-local computation has to happen inside the recursive net's think calls and be written into 15x256 latent slots. That includes binding a name to a number, counting list items, applying op 1 then op 2, comparing table rows, and tracking swaps.
- There is no big LM to lean on. This removes the sandwich's failure (the decoder re-reading the words) entirely. The 'talker re-reads the question' leak shown in code-map 6.3 has no counterpart here.

What can still leak or confound:
- (a) Local families the reader can half-solve. digits_parity uses the last digit, and copy_word/letter_ops are near-copies. These are reading, not reasoning; report them separately.
- (b) The real question changes from 'does the reasoner carry the answer' (yes, trivially) to 'does the RECURSION do the work, or would one pass of the same 2-layer slot net do'. That is measured by the trained no-recursion arm E and the loops:K / swap_mid lesions, not by the donor swap.
- (c) Data shortcuts that any model takes: syllogism 'No -> no', and object_track 'last recipient' (data.md section 1). Report these separately.
- (d) The answer-format trick (LSB-first answers) could make a win that has nothing to do with recursion. Control D (plain_tf with reversed answers) isolates it.

## params

All counts are shown: built on CPU with the harness vocab (108 ids). FLOPs are shown from torch FlopCounterMode for matmuls and convs plus analytic attention, at batch 256 and prompt pad 189.

~3M default: d=256, 8 heads, mlp 5, 2 net layers, 2 conv layers, 15 latent slots, n_think 2, t_cycles 2, n_sup 2.
- Total 3,106,048, against plain_tf d256 L4 3,244,544 (-4.3%).
- Reader 738,304: char_emb 27,648 (tied with the talker), pos 53,248, 2 convs 655,872, LayerNorms 1,536.
- Reasoner net 2,360,832: 2 x 1,180,416. Per layer: self-attn 262,144, cross-attn 327,680 (q, o, kv), MLP 655,360, 3 RMSNorms 768.
- Slot ids, role and output norm: 6,912. Talker: 0 extra.

~10M: d=480, 6 heads (80 per head), otherwise the same.
- Total 10,769,760, against plain_tf d384 L6 10.775M.
- Reader 2.460M (conv 2.305M), net 8.297M, other 12.5k.

Training FLOPs per update (batch 256):
- plain_tf 3.2M: 0.87 TFLOP (1.00x).
- trm_text 3M: 0.91 (1.04x).
- trm_text no-recursion arm: 0.42 (0.49x).
- plain_tf 3.2M n_loops=2: 1.73 (1.99x).
- plain_tf 10.8M: 2.77.
- trm_text 10M: 3.11 (1.12x plain_tf 10.8M). With n_sup=3 it is 4.19, which is over budget.

Inference per example:
- trm_text 3M: 1.5 GFLOP (10M: 5.2).
- The harness's cache-free plain_tf greedy decode: 10.2 GFLOP (9 steps).
- plain_tf with a KV cache would be about 1.1 GFLOP (estimate).

Wall-time risk (shown count, suggested consequence): about 1,608 aten ops per update against 168 for plain_tf, with matmuls about 8x smaller. Expect 1.2-1.8x plain_tf wall time: 23-35 min 3-way shared, against plain_tf 3.2M's 1,173 s. So run a speed check first (see training).

## pretrained_parts

None. Every weight is randomly initialised and trained only on the 200k skills rows.

## training

Loss: deep supervision inside each harness update, so the model stays stateless.
- L = (1/N_sup) * sum over s=1..2 of CE(head(y_s), target), where target is the reversed answer chars + EOS. Slots after EOS are ignored (-100), as in plain_tf. Logits are cast to .float() under bf16.
- y_s and z_s are detached between steps. Inside a step, only the last cycle is backpropagated (TRM: full backprop through one recursion beat the 1-step gradient, 87.4 vs 56.5 on Sudoku).
- The aux dict logs ce_s1 and ce_s2. Expect ce_s2 < ce_s1 by 20% or more at the end, or the refinement is idle.
- No step supervision and no Q-halting in the decisive test.

Optimiser: the harness as it is.
- AdamW (0.9, 0.95), weight decay 0.1 on Linear and Conv weights. None on embeddings or norms; the slot and role embeddings are nn.Embedding precisely so train.py exempts them.
- lr 1e-3, warmup 1000 (plain_tf uses 300; post-norm recursion wants a gentler start), cosine to 10%, grad clip 1.
- Batch 256, 24,000 updates, --bf16, shuffled order, seeds paired with the plain_tf arm. No EMA (TRM uses EMA; add it to both arms or neither).

Needed beyond the harness:
- (1) Register 'trm_text' in models/__init__.py.
- (2) A 'rev_ans' flag in plain_tf (about 12 lines) for control D.
- (3) The box job builds a second dev set with --dev-per-cell 200 (same train hash, data.md section 0). It runs `python -m custom_io.evalx --run <run> --data <data_big> --device cuda` inside the job, because the .pt checkpoints are not shipped back.

Before screening (about 3 min of GPU):
- A 2,000-update smoke run alongside 2 other jobs. Loss must fall smoothly, with no spikes above 2x the running mean. If not, use lr 5e-4.
- Projected 24k time must be 25 min or less. If it is over, either run 2-way shared, or pad prompts to 208 (static shapes) and torch.compile Layer.forward (two graphs: think and answer).

Optional follow-up after the decisive test (one change): intermediate targets. At sup step s, the target is the result after s operations, parsed from the 'steps' field for the five chain families (needs n_sup >= 5). 2603.21676 found per-step supervision hurt extrapolation, so treat it as its own test.

## predictions

All untested; these are my estimates against plain_tf at matched params, 24k updates.

Plain_tf 3.2M reference (shown, 4 seeds): in_dist 75.7 (sd 1.7), multi-step in_dist 62.1 (2.3), variant 20.2, family 0.8, answer 43.7, frame 71.2, vocab 60.5.

TRM-text 3M:
- in_dist: 75, range 68-81. Most likely a tie (within 3).
- multi-step in_dist (12 families x 40 rows): 66, range 55-76 (+4).
- 5-chain panel (chain_ops, chain_story2, story_chain3, state_update, var_chain; 200 rows each from the big dev build): 50%, range 35-65, against plain about 37-45% (+10).
- Worst families:
  - chain_ops 8% -> 25% (5-50)
  - var_chain 25% -> 40% (20-65)
  - state_update 40% -> 55% (30-80)
  - table_lookup 23% -> 35% (20-60)
  - verify_claim 62% -> 75%
- Possible losses where 15 slots must hold exact characters: cipher_map 55% -> 45% (25-70), list_index 50% -> 50% (30-75).
- variant: 20, range 16-25 (no change). The layout-only variant rows ('Question: ... Facts: ...') might gain 5-15, because slot cross-attention ignores order (suggested).
- Held-out families: 1%, range 0-5 (no change; recursion does not create skills it never saw).
- answer 45, frame 70, vocab 58 (each within 3 of plain).

10M against plain_tf 10.8M (shown, 1 seed: in_dist 76.0, multi-step 64.0, family 3.8): in_dist 76 (69-82), multi-step 68, chain panel 52 against about 43. There is less headroom because n_sup is cut to 2 at d=480.

Honest odds:
- P(chain panel +8 or more AND in_dist within -3) is about 0.3.
- P(no-recursion arm at least 10 below on chains) is about 0.6.
- P(a clear overall in_dist win of 3 points or more) is about 0.25.

Most likely outcome: a tie overall, with a modest multi-step win. Where it can still win even on a tie:
- 'Think longer' (loops:4 above loops:2 on 4-5-step chains), which plain_tf cannot do.
- One parallel decode pass.
- A reasoner that provably carries the answer at no accuracy cost.

## evidence

For this design (papers.md):
- 2510.04871 TRM: from scratch, 2 layers beat 4 (87.4 vs 79.5); full recursion backprop 87.4 vs 1-step 56.5; Sudoku 87.4 against 0 for direct prediction. Shown on grids only.
- 2506.21734 HRM and the ARC Prize analysis: most of the gain comes from outer-loop deep supervision.
- 2512.14693 URM: recurrence beats unshared depth at equal FLOPs (ARC-1 40.0 vs 23.75).
- 2609.39967: OOD arithmetic 71.2 for the recursive model against 7.5 for a same-size dense model. Bounded, normalised state and the gradient horizon matter.
- 2502.17416: a looped 1x12 net matches a 12-layer net on addition and p-hop.
- 2604.07822: looping enables systematic composition.
- 2202.05826: re-read the input every iteration.
- 2107.14795 Perceiver IO: latents read the input by cross-attention, outputs come from queries.
- 2402.01032: keep raw characters addressable rather than compressing them into a state.
- 2307.03381: LSB-first output helps small models.
- 2405.17399 Abacus: digit-position marking.

Repo (shown):
- results-digest #22: tiny looped reasoners beat their plain twins (6-digit sums 298 vs 154 of 300; 6x6 grids 291 vs 250), with structured I/O.
- CALIBRATION: plain_tf's weakest families are exactly the depth-bound ones. Checked against RESULT.json at 24k (the task text quotes the 8k figures): chain_ops 3-4/40, var_chain 8-11, table_lookup 8-10, state_update 13-21, list_index 19-21, verify_claim 24-26.

Against, or cautionary:
- 2512.11847: TRM's ARC accuracy comes mostly at the first recursion step and depends on a task ID.
- 2603.21676: on the text task, the looped model only tied a fixed-depth transformer (83/60 vs 81/58), and per-step supervision hurt extrapolation.
- 2511.14761: a non-recursive ViT with better input encoding beat TRM.
- 2604.07822: needed more than 1.3M steps to grok; we have 24k.
- 2207.10551: weight sharing loses on general language modelling.
- Repo calibration: tf2x4 (plain TF looped 4 times, 1.7M) scored 59.3 against 65.7 at 8k.
- Repo digest #11 and #15: more core loops never helped.

What is different from what failed before:
- The sandwich loop was nearly stateless (|e|/|h| = 44, 0.6% change per round) and a 1.2B decoder re-read the words. Here there is no LM, the injection and the state are on the same scale, and the talker cannot see the prompt.
- Digest #17 (13-15%) used a 475-way class head, batch 1, 6k updates and LM features computed once. Here: character answer slots, 24k x 256 updates, and deep supervision.
- tf2x4 had no deep supervision and half the params.

## lesions

All expected sizes are untested.

- (1) Trained no-recursion arm E: same class and params, cfg {"n_think":1,"t_cycles":1,"n_sup":1}. It is one think call plus one answer call, a plain 2-layer slot Perceiver. Expect -10 to -25 points on the 5-chain panel against A, and within 5 on copy and lookup families. This is the main proof that the RECURSION carries the answer. If A - E is 3 or less, the design is just a small Perceiver.
- (2) loops:K sweep (automatic in train.py: K = 0,1,2,4).
  - loops:0 gives about 0% (format check).
  - loops:1 drops the chain panel 8-20 and in_dist 3-10, with copy families flat.
  - loops:4 (2x trained) stays within 3 of loops:2 if the fixed point is stable. A gain of 0-8 on rows with 4-5 steps is the 'think longer' signal. A drop of more than 10 means an unstable state (a risk).
  - Report accuracy per step for each family (2601.10679 and 2512.11847 recommend this).
- (3) swap_mid (custom): after supervision step 1, swap (z,y) with a donor row, then run the last step on the row's OWN prompt. One-step families should recover to 80% or more of intact. Chain families should lose 15 or more points; a step's work carried in the state cannot be redone in one step.
- (4) The harness donor swap and shuffle_state (state = y). Expect about 100% donor match, with exact near the family floor. This passes the project mark (a drop of 20+ points and at least 50% donor matches) BY CONSTRUCTION. Report it only as a wiring check, not as evidence.
- (5) zero_state: 0% (format check).

## decisive_test

Screen: one batch of 3 runs sharing the GPU, seed 1 each, 24k updates x 256, about 25 min (about $0.25).
- A = trm_text default (3.1M).
- B = plain_tf d256 L4 H4 (3.2M), lr 1e-3.
- E = trm_text no-recursion (3.1M).

Eval: the six harness splits, plus the 5-chain panel (1,000 rows from the 200-per-cell in_dist build), plus lesions.

Pass marks, fixed now:
- (i) chain panel A - B >= +8 (about 2 sd of a 1-seed difference; plain multi-step seed sd is 2.3).
- (ii) in_dist A >= B - 3.
- (iii) chain panel A - E >= +10.
- (iv) loops:1 costs A at least 8 chain-panel points.

Proves it wrong:
- chain panel A - B <= +3 (the TRM structure gives no multi-step benefit at this size), or
- A - E <= +3 (the recursion is idle), or
- in_dist A < B - 5 (the reading bottleneck costs more than the recursion gains).

If the screen passes, confirm with 6 fresh paired seeds of A vs B (12 runs, about $1). Pass: mean chain-panel difference >= +8 with 5 or more of 6 seeds positive, mean in_dist difference >= -1.5, and pooled-5 difference >= 0 (pooled-5 sd is about 1.0).

Attribution arms, 2 seeds each if budget allows:
- C = plain_tf n_loops=2 (2x FLOPs).
- D = plain_tf with reversed answers.
- Need A - C >= +5 and A - D >= +5 on the chain panel. Otherwise the win comes from compute or answer format, not from TRM.

## implementation

Files:
- custom_io/models/trm_text.py (about 165 lines): classes Layer, ConvReader, TRMText(Model).
- MODELS['trm_text'] = TRMText in custom_io/models/__init__.py.
- plain_tf: a rev_ans flag (about 12 lines). In _build, reverse the answer chars before the EOS; in generate, reverse the decoded string.
- Queue job custom_io/queue/04-trm-screen.sh (A, B, E), plus an in-job evalx on data_big.
- Total about 200 lines, 2-4 h including `python -m custom_io.test_harness`.

A working, untrained prototype that passes the harness's evaluate, donor_eval and every lesion on CPU:
/tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/trm_proto/trm_text.py
FLOP and op probes: probe.py and ops.py in the same folder.

Key pseudo-code:
```
def f(z,y,kvs,mask,think):
    s = cat([z,y],1) + slot.weight + role.weight[0 if think else 1]
    for L,kv in zip(layers,kvs):
        s = L(s, kv if think else None, mask)
    return (s[:,:M], y) if think else (z, s[:,M:])
cycle    = 2 x f(think) then f(answer)
sup_step = no_grad(cycle) then cycle
loss: X = reader(ids,mask); kvs = [L.kv(X) for L in layers]; z = y = 0
      for s in range(n_sup):
          z,y = sup_step(...); tot += CE(head(y), rev_tgt)/n_sup; z,y = z.detach(), y.detach()
state(batch,loops) -> y        talk(y,batch) -> argmax, cut at EOS/PAD, reverse
```
Reversed targets: t_j = a[n-1-j] for j < n, EOS at j = n, -100 after. Checked: '65' -> [5, 6, EOS].

Gotchas:
- (1) The tied head needs small init. Default nn.Embedding init gave an initial CE of 37 against ln V = 4.7 in my probe; use std 0.02.
- (2) Slot and role ids must be nn.Embedding (an nn.Parameter would get weight decay 0.1 in train.py), and must be re-initialised to std 1 after the 0.02 init loop. Otherwise slots lose their identity once the post-norm state reaches RMS 1.
- (3) The answer call must pass kv=None. That is the only guard against a prompt leak into the talker. Add a unit test: the answer call with another row's kv must give the same y.
- (4) Compute the reader and the K/V once, WITH grad, and reuse them inside the no_grad cycles. Never wrap the reader in no_grad.
- (5) `n_loops = n_sup`, so the train.py sweep runs loops 0, 1, 2, 4.
- (6) About 1,600 ops per update makes it launch-bound. Use the speed check; compile only after padding to T = 208.
- (7) Dev family answers longer than 8 chars cannot be reached with 9 slots (5 of 160 rows).
- (8) For 'swap_mid', add it to LESIONS and override generate; everything else goes through Model.generate.

## risks

- (1) Reading bottleneck: 15 slots via cross-attention may copy less exactly than full self-attention. cipher_map, list_index, copy_word and passage_qa could drop and cancel the gains on chains. This is the most likely reason to lose on in_dist.
- (2) The recursion collapses to one useful pass. The TRM-on-ARC analysis found most accuracy at step 1. This is detected by arm E and loops:1.
- (3) 24k updates may be too short. Looped models often grok late (2604.07822 needed more than 1.3M steps). Watch whether ce_s2 is still falling at the end.
- (4) Speed: 10x more kernel launches than plain_tf. The run may go past 25 min when shared 3-way; fixes are 2-way sharing or compile.
- (5) Post-norm recursion instability at lr 1e-3. Handled by the smoke run.
- (6) The format confound from LSB-first answers. Handled by arm D.
- (7) Parallel slot decoding can mix two candidate words across slots. Inspect the wrong word answers.
- (8) Single-seed screen noise. The marks are set at about 2 sd, but a true +5 effect can still fail the screen.
- (9) Nothing here addresses held-out families or learning from a few examples (Ben's north star). Expect 0-5% there, as for every from-scratch model so far.
- (10) The 10M version has to cut n_sup to 2 at d=480 to fit the budget. Recursion depth per parameter falls, so the 3M comparison is the fair first test.

## english_and_minecraft_path

English: the char-conv reader and the slot reasoner work for any text, but human English needs far more reading data than 200k templated rows.
- Next step, still nothing borrowed: pretrain the reader and slots with masked-character denoising on simple English (TinyStories scale).
- For sentence answers, widen the answer slots, or add a tiny autoregressive talker that cross-attends only to the final (z,y) state with the prompt masked. That keeps the rule that the talker sees only the reasoner.

Minecraft: TRM's loop maps directly onto an agent's think loop.
- x is the observation (a local voxel or pixel patch, inventory and goal text) read by a local conv reader.
- z is a latent plan carried across game ticks, the way TRM carries state across supervision steps.
- y is a set of action slots, trained by deep supervision from demonstrations, with a halting head so the agent thinks longer when unsure.
- Learning new skills from a few demos placed in the input is untested.

