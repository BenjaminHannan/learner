# Sleep-B addendum 19: the two-step recipe on the new small tier, LFM3-1.7B (written 2026-10-27 ~20:10Z, before any LFM3 sleep run)

Labels: shown / suggested / untested. Week-2 world, tests and scoring as addendum 9 and 17. Not the village model, not the card
experiments.

## Why
- Ben (2026-10-27 19:45Z): "remember we use LFM3 now instead of K2. I think that's one is just objectively better and it runs faster."
  The small tier is now LiquidAI/LFM3-1.7B, so his goal (2026-10-25: two-hop >= 75 of 78, weights only) now applies to LFM3.
- Like addenda 11 (K2) and 12 (Qwen3.6), this is a transfer test: the best recipe so far, moved to the new model. It is not a tuned run.
- The recipe is addendum 18's arm (arm B + the 570-question gate + the fixed two-step card writer). Addendum 18 has no K2 result yet,
  so the writer fix is not shown on any model. That makes this run a test of two things at once (the model and the writer). It is
  accepted here because the K2 runs that would separate them may not happen. If addendum 18 does run on K2, the separation is
  reported then.

## Model
LiquidAI/LFM3-1.7B, revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd, bf16, `trust_remote_code` (Lfm3ForCausalLM).
- 24 layers: 13 gated short-conv, 6 global attention and 5 sliding-window attention (window 256). 128k vocabulary, tied embeddings.
- ChatML template. Thinking off is the template's `enable_thinking=False`, which ends the prompt with `<think></think>`. Thinking on
  leaves `<think>` open; it closes with `</think>` and a turn ends with `<|im_end|>`.
- LoRA rank 16, alpha 32 on every attention q/k/v/o_proj, conv in_proj/out_proj and feed_forward w1/w2/w3 (142 modules, about 16.1M trainable
  parameters). The attention `gate_proj` is excluded.
- Every think path K2 uses runs on LFM3 the same way: the names pass, the REM `q_think` writer and the report-only `--think-eval`.
  LFM3 has no effort levels, so K2's effort argument has no effect.

## Code
Commit f35dd7e840 (the LFM3 port): sleep1.Lang lfm3 mode (Lang.think / .end / .shut), train.is_lfm3, the LFM3 LoRA targets,
k2_chain_probe on LFM3.
- **Shown (CPU):** with K2 and Qwen, smoke result JSONs (addendum 18's flags) are identical to the code before the port apart from
  timing, and --selftest passes. The LFM3 smoke (a tiny random LFM3 with the real config, remote code and tokenizer) finishes, with the
  REM think path running.
- **Shown (real tokenizer):** the tags are single ids (`<think>` 124901, `</think>` 124902, `<|im_end|>` 124900 = eos). Stage 2
  (thinking + `</think>` + answer + `<|im_end|>`) equals the template's own finished turn. The regex hits 142 modules on the real
  layer list.
- **Shown (CPU, real weights, fp32, results_a19/pad_check):** LFM3's batched, left-padded greedy generation (padded the way
  Lang.generate pads) gives the same text as one prompt at a time, and the last-position logits match exactly (max difference 0.0,
  3 prompts of 18-63 tokens, 24 new tokens). So the conv layers do not leak left padding.
- Untested: LFM3 training speed and memory on the GPU, and its thinking length (the 512-token caps are K2's).

## Pre-check (cheap; generation only, Week-1, no training)
`k2_chain_probe.py --model LiquidAI/LFM3-1.7B --revision 40ebe0aa... --variants q_think --tries 1 --gen-bs 24 --also-fixed`, one night
(4 cycles), on Ben's PC.
- **Stop (the port is broken; fix it before any full run)** if the probe has no complete result, the fixed writer keeps 0 chain cards,
  or fewer than 14 two-hop tests are reachable (half of K2's 27; reachable means the tagger made both facts eligible).
- Otherwise the full arm runs. The probe's fates and its dreamed-forward count (against ceil(0.88 R), addendum 18's bar) are reported
  as the writer's quality on LFM3. They are not a gate here, because recall and no-harm on LFM3 are needed whatever the writer does.

## The arm (Week-2, seed 1)
- **l3_g570_w:** `--arm ab_ob_b4_nb --model LiquidAI/LFM3-1.7B --revision 40ebe0aa... --week data/week2.json --seed 1 --arc-base
  --tok-budget 256 --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval
  --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96 --reword data/week2_reworded.json --gen-bs 24`.
  That is addendum 18's command with the model swapped. If it runs out of memory, it reruns at `--gen-bs 16`.
- Everything else is the recipe's default: lr 2e-4, batch 16 + 8 replay, KL weight 1, SHY, steps and dream budgets.

## Marks (fixed now)
- **G (Ben's goal):** two-hop >= 75 of 78.
- **P1 (the recipe transfers):** recall C2+C4 >= 88.5. That is the size-matched reference, Qwen3.5-2B ab_ob_b4_nb seed 1 (91.5), minus 3.
  - **Wrong if** the tagger's mention recall is >= 0.5 but recall is < 60. Then note-taking works and the learning does not transfer.
- **P2 (two-step transfers):** two-hop >= 39 of 78 (K2 arm B's), reported with a paired exact McNemar against arm B on the same
  questions.
- **No harm:**
  - ARC-Easy 500 >= LFM3's own pre-sleep score - 5 (`--arc-base`);
  - diary pooled >= LFM3's own base_diary - 5;
  - changed-new >= 53.3 (B's).
- **Reported, not marked:**
  - the pre-check's fates and both writers' counts;
  - tagger recall and precision, and names-pass counts;
  - chain cards kept per night and thinking tokens;
  - two-hop by the night each test's chain became dreamable;
  - each night's gate score and undo;
  - reverse, routine, new-wording recall and think-eval;
  - paired comparisons with K2 arm B and, if it exists, addendum 17's run;
  - wall time per night against K2's.
- **Expectation (not a mark):** recall 85-95, two-hop 35-65, about half of K2's wall time per night. Suggested only.

## Compute and PC order
Free: Ben's PC, in this thread's next slot (after the loop thread's hops runs and race-mini v2; the coordinator's order of 2026-10-27
19:35Z). The pre-check is about 1 h, the arm about 4-7 h, and it stops itself if it would pass 10 h. This takes the slot that addendum 18
(K2) had. If the pre-check stops the LFM3 arm, the slot runs what addendum 18 planned (addendum 18 if its pre-check said Go, else arm A).
Addendum 15's R8 and V8 (K2) keep their places after it. Arm A does not run when this arm or addendum 18 takes the slot, so addendum 15's
base is then the defaults (the sealed rule's fallback, as addendum 18 records). Chain script: pc/sleepb_pc10.sh, which takes over from
sleepb_pc9.sh once addendum 17 has passed its turn on.
