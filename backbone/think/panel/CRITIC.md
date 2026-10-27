# Completeness critic: FINAL-DESIGN.md (G-STS), 2026-10-24

Labels: **[shown]** = I read it in code or data, or recomputed it today. **[suggested]** = my inference or arithmetic. **[untested]** = nobody has run it.
The village pilot (Qwen3.5-0.8B) and the LFM2.5/tau2 scale-up are kept apart below. No card experiments are involved. v1 appears only where FINAL uses it as a prior.
Nothing under /home/user/learner was edited. Nothing was trained and no GPU was used. The only things I ran were CPU reads of the scratchpad data and weights, and re-runs of the panel's own analysis scripts.

## A. Pilot: bugs and leakage (fix before any GPU run)

1. **The answer pass writes into the shared prompt cache, which leaks the gold answer into later laps.** [shown, code]
   - FINAL says the answer pass "continues from the un-forked prompt[:-1] cache", and the pseudocode calls `answer_ce(C, …)` on the raw C.
   - In transformers 5.20.2, `DynamicLayer.update` reassigns `self.keys = torch.cat([...])` on C's own layer object (cache_utils.py ~135). `update_recurrent_state` always runs `copy_`, for any sequence length (~1133). `update_conv_state` runs `copy_` for multi-token chunks whenever `has_previous_state` is set (~1112). `Qwen3_5GatedDeltaNet` calls both on every cached pass (modeling_qwen3_5.py 570-628).
   - FINAL's §3 line "in-place updates happen only in single-token decode" is therefore **wrong**.
   - Consequence [suggested]: after lap t's answer pass, C holds the teacher-forced gold answer. Lap t+1's slot pass reads it, so later laps can copy the answer in training but not at eval (eval uses a clone). Training-time lap curves would rise for the wrong reason, eval would not match training, and autograd may fail on the in-place `copy_`.
   - Fix: run every answer pass on its own ForkCache. Extend T2 so it asserts `torch.equal` on C after the answer passes too. Add a test that changing the answer tokens leaves the lap-t+1 board unchanged.

2. **The harness cannot yet produce the numbers the pass marks need.** [shown, code]
   - `backbone/train.py evaluate()` saves no per-row predictions (only 40 examples) and does not group by `depth`. So the paired per-seed rules (R1, R2's flip-based noise model), "report by depth", flip counts and M2 cannot be computed for re-scored A and B.
   - `--load-adapter` skips training, so **A+ has no code path**. It also needs `PeftModel.from_pretrained(..., is_trainable=True)`.
   - `backbone/think/run_box.sh` uses one `STEPS` (default 418) for every job. Its arms `a` and `b` **retrain** with train.py instead of re-scoring. It has no A+, ablation or probe (Pdepth) wiring, and passes no stage-A adapter to `t`. `think1.py` and `summarize.py` do not exist yet.
   - With `STEPS=1254` set globally, A and B would train 1,254 steps. Left at the default, T would train only 418.
   - No stage-1 adapter is in the repo, on HEAD or on the branches I checked. So "seed s's frozen A adapter" probably means retraining. The same arm and seed has already given 67.78 vs 65.94 (RESULTS-stage1.md).

3. **e₀ is never clamped, and its learning rate is large for its scale.** [shown ρ; rest suggested]
   - ρ (median row RMS of `embed_tokens`) = **0.0195**, with median |element| 0.0129 [shown, read from the safetensors].
   - Adam at lr 1e-3 moves each element ~1e-3 per step, i.e. ~5-8% of its size, so e₀ can drift a full ρ in ~20 steps.
   - The pseudocode clamps only after lap updates, so pass 0 can use oversized slots and the first clamp then causes a lap-0→1 jump unrelated to thinking.
   - Fix: clamp e₀ as well, and either parametrise e₀ in units of ρ or give it lr ~1e-4.

4. **The "gate opened" check is too weak, and clipping is shared.** [suggested]
   - With α at lr 1e-2 under Adam, α moves ~0.01 per step from gradient noise alone. Mean |tanh α| > 0.02 at step 150 therefore does not show the board is useful.
   - Add to the mechanical gate: the swap-lesion Δ on the 512 dev rows (> 0.5 point), and a refiner gradient norm that is not near zero.
   - Global clip 1.0 is shared by α and the refiner. α's gradient (a whole SDPA output) can dominate the norm and starve the refiner. Clip each group separately.

5. **Cross-row leakage bug class.** [suggested]
   - If the refiner uses `nn.MultiheadAttention` with its default `batch_first=False`, a [B,K,d] board attends across rows of the batch.
   - T6 catches this only if its batch holds ≥2 distinct rows. Add a batch-permutation invariance test.

6. **Data order.** [suggested] "Reshuffled with seed s" on `random.Random(s)`, as train.py uses, makes T's first 418 steps re-see exactly A's rows. Use a separate stream so T, T1 and A+ see new rows in the same order.

## B. Pilot: controls and wrong-reason passes

7. **No compute-matched non-recurrent control.** [suggested]
   - T1 (L_max=1) runs 2 slot passes and T@8 runs 9, so R4 cannot separate *sequential feedback* from *more backbone compute over slots*.
   - LRT's 56.7 vs 47.5 (R4 notes) was an **equal-budget** non-recurrent comparison [shown, notes]; T1 is not one.
   - Add one cheap seed-0 arm: either K=144 slots with one refinement (same token-passes as 9×16), or 9 independent passes with no feedback between them.
   - repeat-Δ1 is close to this but underspecified (is the board e₀ + t·Δ₁? is it clamped?).

8. **The lap-0-weighted uniform loss may flatten the curve, and the alternative is tested on seed 0 only.** [suggested]
   - Averaging CE over t = 0..L_max pushes the earliest laps to be good exits. That works against R1's ≥1.5 slope.
   - TaH found per-lap loss −4.3 vs final-only [shown, R3], though in a different setting (full fine-tune, selective iteration).
   - Fix in advance which loss variant goes to seeds 1-2 if seed-0 lastloss beats uniform. Otherwise the 3-seed arm may be the weaker variant.

9. **The noise model is too optimistic.** [shown inputs, suggested consequence]
   - The same seed and steps on two boxes gave 67.78 vs 65.94 (1.84 points), so run SD is ≳1.3, not the 0.9 that FINAL uses (0.93 is the 3-seed SD of A).
   - At SD 1.3, a true mean at the 70.12 bar falls below the 68.7 futility line ~14% of the time, not 6%.
   - R2's 0.3 tolerance uses only binomial within-run error. Score one checkpoint twice in the new harness to measure eval nondeterminism (bf16, batch composition) before trusting 0.3.
   - The arithmetic itself checks: sqrt(0.06/8675)/√3 ≈ 0.15, so 2 SE ≈ 0.30; (70.12−68.7)/0.9 = 1.58 SD, p ≈ 0.057 [shown].

10. **A+ is underspecified.** No learning rate or schedule is given for continuing an already cosine-decayed LoRA: re-warm to 2e-4, or lower? A weak A+ inflates G. A+ is also a single seed unless A+−A ≥ 1.0, yet it is mixed into a max with 3-seed means. B gets no extra-steps control. Since B ≈ A this matters little.

11. **Headroom.** [shown inputs]
    - The bar is 70.12. A2 (2B + LoRA) scored 69.81. where_before + plan_get = 2,019 rows at 33.5 / 37.8 (verified, from the 65.94 run).
    - Lifting those banks by 10 points gives only +2.3 overall [suggested].
    - FINAL already expects G to fail (P ≈ 0.10). The decision that matters is whether a partial result (R and M1 pass, G fails) justifies Think-1b, and that is preregistered. Good.

## C. Pilot: compute and memory estimates (unverified)

12. **Step time is probably optimistic.** [shown inputs, suggested]
    - Arm A ran at 3.3 s/step on an A100 (probes2 result: 1,384 s / 418 steps) and B at ~4 s (RUNLOG).
    - A T step adds a no-grad prefill of the same 4×2k tokens per micro-batch, plus 9-13 slot passes and 9-13 answer passes with full BPTT, over 4 micro-batches, on a 5070 Ti.
    - So "2-3 s/step, ~1 h/seed" is unlikely. 3-10× that is plausible.
    - RUNLOG says Triton (fla) needs a C compiler. If fla is missing on the PC, DeltaNet falls back to the slow torch chunk path.

13. **The eval sweep costs more than 1.5-2× A's eval.** [suggested] Each row decodes separately at 8 lap values (0, 1, 2, 4, 8, 12, 16, 24), plus 25 slot passes. Expect several times A's eval cost, multiplied over T and T1 at 3 seeds, 4 lesions and the ablations. No total PC-hour budget is given.

14. **The clone is larger than stated.** [shown config, suggested arithmetic] GDN state is 18 layers × 16 heads × 128 × 128 ≈ 4.7M values per row, ~19 MB in fp32 (`mamba_ssm_dtype` float32), not "a few MB". At eval batch 64 that is ~1.2 GB per clone, so clone sequentially.

## D. Mac speed rule (LFM2.5, tau2)

15. **The base model may already be under 30 tok/s at real tau2 contexts.** [shown inputs]
    - Thinking-ON tau2 prompts: mean 6,801, p90 9,368, max 12,493 tokens (re-run of an_think.py on backbone/think/panel/probe/think.json).
    - The 35.4 tok/s (2 agents) bench used a short prompt. Measure 2-agent decode at 9-12k tokens, not only 6.4k and 9.4k, before attributing any failure to the board.

16. **Graft 1 adds a per-token cost that FINAL does not count.** [suggested]
    - The gated board read is an extra SDPA plus a gate multiply at 10 attention layers on *every decoded token*.
    - D6's "zero per-token cost" no longer holds once the slots are read through a side branch instead of sitting in the cache.
    - Likely 0.5-2% from mlx kernel dispatch. That is close to the whole margin under the ≥97%-of-base mark. Measure it in step (c).

17. **Two-agent burst contention, and the per-episode mark.** [shown inputs, suggested]
    - Thinking-ON episodes have 13.8 generations on average, p90 18, max 22 (shown).
    - At K=8, L=4: 5 × ~90 ms ≈ 0.45 s alone, ~0.9 s if serialised behind the other agent. That gives ~12 s per episode on average and ~20 s at the max. The K=16 ablation (5 × 139 ms) gives ~19-30 s.
    - So the "≤+15 s per episode" mark is fragile at K=8 and fails at K=16.
    - Thinking-OFF episodes with repeated failing calls are longer.

18. **"Time-averaged decode" is undefined.**
    - Say whether the other agent's prefills and bursts count.
    - The 10.8 s + 22.4 ms·ct + 3.43 ms·pt fit is reproduced [shown], but it was fitted at concurrency 1.95. Its 22.4 ms/token (44.7 tok/s) is faster than the 2-agent bench's 28.2 ms, so its terms are confounded [suggested].
    - Fix the exact measurement script before the run.

## E. LFM2.5 distillation and RL

19. **Thinking is not stripped within a user turn.** [shown, template]
    - The LFM template keeps thinking for assistant messages after the last user message (`keep_thinking = preserve_thinking or loop.index0 > ns.last_user_index`).
    - 41% of user turns contain more than one assistant generation [shown, think.json].
    - So the teacher's later tool-call generations condition on its earlier thoughts, while the student's board resets every generation. Either carry the board within a user turn or accept a teacher/student mismatch.
    - FINAL's "the template strips old thinking" is only half true.

20. **Budget and rollout time are not added up.** [shown inputs, suggested arithmetic]
    - Brief: "this week's remaining credit is only a few dollars". FINAL plans $4 of Haiku, unestimated A100-80GB hours for bf16 24B training, and an RL cap of $15.
    - One GRPO step (G=4 × 16 tasks = 64 episodes) takes 64 × 597 s / 2 agents ≈ **5.3 Mac-hours** (mean episode 597 s, concurrency 1.95, both shown).
    - The $15 cap buys ~10-23 steps (the lower cost bound per step is $0.64, not $1), i.e. 2-5 days of Mac time for an RL stage too small to matter. This needs Ben's explicit approval.

21. **tau2 noise.** [suggested] The 23 and 30 are single trials. Binomial SD is ~3 tasks per run, so the 7-task gap itself is uncertain. Run OFF and A-dist at the same 4 trials as T, paired by task. FINAL's step (a) paired table and (b) guard run are the right first moves.

22. **Untested conversions.**
    - mlx 4-bit → dequantised bf16 HF weights needs a converter (group-wise scales and biases).
    - HF `Lfm2Moe`'s expert dispatch is slow on an A100.
    - Both are listed, but neither has a cost or time estimate.

## F. Factual and consistency slips in FINAL

- **Halting rule and decision points.** §1 says D5's "halting rule, decision points" are kept, but the spec has neither. D5's rule (add a halt only if oracle headroom is ≥2 points) should be written in [shown, design-halt.md].
- **"Detached hinge" ablation.** It is listed but never defined in FINAL. D5 defines it as 0.5·relu(CE(L+4) − sg(CE(L))) on 25% of rows.
- **Thinking length.** "Mean 284 tokens/turn" is labelled shown, but it is reasoning characters ÷ 3.68 (an3.py), an estimate. Mark it suggested.
- **Mixed runs.** Pdepth 74.47 (the 65.94 run) is compared with P0 82.42 (the 67.78 run). The per-bank A numbers are also from the 65.94 run. Say so.
- **LFM refiner size.** 10.53M counts e₀ at K=16. At the default K=8 it is ≈10.51M [suggested arithmetic]. The pilot's 2,644,016 checks out (W_in with bias, bias-free attention) [shown arithmetic].
- **"Recurrence is the only route to a second hop."** This overstates. One pass already does multi-hop: A answers depth 2-3 rows. It is only the board's only route to information beyond one pass.
- **B loop count.** RESULTS-stage1.md labels B seed 1 "full (2 loops)", while the default is `--loops 3`. Check which was run before using B_ref = 67.12.
- **Verified correct [shown]:**
  - training depth ≤3;
  - 1,558 validation rows at depth 4-6 (18.0%);
  - 36.8% of rows at depth ≤1;
  - 2,019 where_before + plan_get rows;
  - Q7/Q8 6.0/43.5 vs 79.1/98.1;
  - A+ 537-step −0.32;
  - A2 69.81;
  - the D2 probe numbers (+0.355 ± 0.090; −0.04 / −0.15 / −0.28 / −0.31);
  - the literature numbers (LRT, INTACT, Flamingo, HybridAgent, TaH, Shapiro, CODI on own traces) match R1-R4;
  - the per-pass Mac arithmetic (1−(60/64)^16 = 0.643; ~139 ms / ~90 ms at 64 GB/s).

## G. Sealed village test

- **Nothing in FINAL requires opening the test** [shown]. build_data.py never generates `test`, and `backbone/genlab/generalize/probes.py` refuses any split outside {train, validation}.
- **Risk 1: validation turns into a dev set.** Validation is the only held-out set. It will be used for the futility stop, lesions, ablation choices and Think-1b, so it becomes a development set with no untouched confirmation set behind it. Accept that, or preregister that only L=8 at 3 seeds counts.
- **Risk 2: a "fresh confirmation set".** Do not regenerate "new validation shards" unless the generator's split config (config, not data) shows they cannot coincide with test.
- **Risk 3: Think-1b's training data.** Its depth 4-6 chains must come from the train profile and must not reuse the Pdepth probe seed (101). Otherwise M2 is contaminated.

## H. Hygiene
- Commit the prereg and its sha256 before seed 0, as the repo does for every PREREG-*.md.
