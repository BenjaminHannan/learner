# Think-1 research sweep: what actually moved benchmarks (2026-10-24)

Four literature sweeps written today by research subagents. The full notes, with arXiv IDs and per-paper tables, are in
`research/R1-recurrent-depth.md`, `R2-latent-cot.md`, `R3-halting-moe.md` and `R4-frozen-workspace.md`.
Labels: **shown** = a number in the paper's own tables; **suggested** = the authors' reading or an inference;
**untested** = nobody has run it in our setting. Many 2026 papers were read through a page summariser; spot checks
against the arXiv and GitHub pages (LRT 2609.01117, ALAR 2606.02871, Project Newt) matched the notes.
Village model and assistant chats only. The small card experiments are not part of this.

## The short version
1. **Nobody has tested silent latent thinking on a multi-turn agent benchmark** (tau-bench, tau2, BFCL multi-turn).
   The 23 -> 30 target is untested everywhere. The nearest results are single-turn tool calling.
2. **Retrofitting a loop onto a frozen model with a small adapter has mostly failed.** The closest prior to Loop-1L is a
   closed GitHub project ("Project Newt": frozen 4B Gated-DeltaNet hybrid, LoRA'd core looped 3 times; also Qwen3.5-0.8B).
   It never beat a compute-matched 1-pass LoRA; only 2-5% of the signal went through the loop (suggested, one author).
   Every positive retrofit trained full weights on 3B-84B tokens (shown).
3. **What did work on a frozen backbone: a small block that refines a few latent slots and hands them to the frozen model
   as extra inputs, run once at the end of the prompt.** LRT (2609.01117): a frozen LLM with a ~11M trained recurrent
   refiner over K latents beat non-thinking CoT by ~19 points on a 5-task average and kept rising with more refinement
   cycles (shown, 3 seeds, per-task training). Differentiable cache augmentation (2412.17747): frozen Gemma-2 2B plus a
   KV-reading coprocessor, GSM8K 21.4 -> 31.4 with 64 latents, rising steadily with latent count; beat pause tokens and CoT
   prompting (shown, but 2e11 tokens of training).
4. **Thinking pays where it changes the action.** Thinking on vs off is worth ~9-10 points on tau retail for Qwen3 4B-32B
   (shown). A "think tool" that writes notes without changing actions hurt retail for several frontier models (shown).
   Looping helps composition (parallel and nested calls, multi-hop), not recall (shown, single-turn BFCL).
5. **Learned halting buys compute, not accuracy.** Wherever a learned halt met the best fixed lap count, it saved laps and
   rarely added points. Joint training of halt and block drifts (our v1 symptom) (shown in several papers). Use fixed laps
   plus a test-time sweep.
6. **Per-token looping is too slow for the Mac rule.** Iterating even 6% of tokens cost ~30% of GPU decode throughput
   (shown). Thinking at a few chosen positions (end of prompt, start of each assistant turn) costs latency, not tok/s.
7. **Gains arrive in 2-4 laps.** Ouro peaks at 4, several 2026 models at 2, and laps past the trained depth often hurt
   ("latent overthinking"). Monotone rises to many laps were seen only for recurrent refiners over latent slots (LRT) and
   for latent count in cache augmentation (shown).

## Design rules we take from it (each one is checked by the pilot, not assumed)
| Rule | Evidence | Label |
|---|---|---|
| Lap 1 must equal the base model: zero-init write-back with a `tanh(alpha)` gate, alpha = 0 at init | Flamingo 70.7 vs 66.5 without gate; LLaMA-Adapter zero-init 83.9 vs 40.8 random init; random memory tokens hurt a frozen agent | shown |
| Gates get their own parameter group and a higher learning rate; log them | gates folded into projections "fail silently"; saturated gates never moved in 10k steps (Newt) | shown / suggested |
| Re-inject the clean input every lap; damp each lap's update | naive recurrence left laps 2-3 worse than lap 1; a quarter step fixes most failures | shown |
| Think at chosen positions, not every token | Think-at-Hard: selective iteration wins, uniform looping flips right answers to wrong; per-token cost ~30% | shown |
| The block must read the backbone's states (cross-attention to cached keys/values), not just the last layer | KV-cache read 26.8 vs last-layer read 23.2 GSM8K (cache augmentation) | shown, one model |
| A few dozen slots at most; laps beat slots | gains rise to 64 latents then flatten; recurrence beat a non-recurrent block of equal budget (LRT 56.7 vs 47.5) | shown |
| Fixed laps, random lap count in training, sweep at test; no learned halt in the pilot | see point 5; our v1 halt result | shown |
| Distil from a teacher where one exists; supervise the action tokens | ALAR: K=4 latents trained with CE on tool-call tokens from the model's own successful thinking rollouts matched thinking mode on BFCL (86.1 -> 89.2) | shown, single-turn |
| Always run lesions: zeroed board, board shuffled across examples, 1 lap | latents collapse to constants in several methods; swapping in another question's latents is the decisive test | shown |
| Compare against a strong 1-pass LoRA with equal steps | every looped arm in Newt lost to it; our stage 1 tie | shown |
| RL only after distillation, with a KL anchor to the frozen model | naive GRPO on latents collapses; INTACT without its KL fell 78.8 -> 42.9 | shown |
| Measure the thinking-ON traces before distilling them | the model's own long traces are where latent distillation fails hardest (12-15% vs 53% on MATH) | shown, math |

## Where the evidence is thin for us
- No result on a hybrid conv/attention MoE like LFM2.5; how short-conv state and the MoE router behave with injected
  slots is untested.
- No result on the board persisting across turns (one model gained 3-5 points on tau2 by keeping last-turn reasoning; suggested).
- The 23/40 vs 30/40 gap has z ~ 1.7 on 40 tasks; scoring the scale-up needs all 114 retail tasks or repeated trials.
