# Sleep-B addendum 11b: two port fixes for K2-Horizon-3.7B before its rerun (written 2026-10-25 ~14:05Z, before the fix code and before any rerun)

Labels: shown / suggested / untested. Amends addendum 11 (sealed, unchanged). Same arms (k2s_bf16, k2s_q4), same world, recipe, seed and pass
marks (No harm, T1, Q1). Not the village model, not the card experiments.

## What happened in the first try (shown, from the q4 run's partial JSON and log)
- **Memory:** the q4 run (box 57667584, RTX 5090, 32 GB) ran out of GPU memory at the first training step of night 3 (30.1 GB allocated,
  `tgt_logits` in `Trainer.step`). Nights 1-2 ran (night 2: 1,008 steps in 818 s). Night 3 is the first with full 2,048-token micro-batches.
  The 3.7B (5.1B with its untied 250k embeddings) holds about twice the per-token activations of Qwen3.5-2B.
- **Names re-read pass:** K2 answered "no" to all 127 names questions on nights 1-3 (Qwen3.5-2B: yes to 38/55, 30/45, 25/36), including
  clear ones ("Lotoufex and Ramein, being siblings" -> "no"; "Keikreth's boat, the Zeiboki" -> "no"; "Kluzhox is based out in Bofobour"
  -> "no"). The prompt is rendered in K2's own empty-thinking format, the same way as the tagger, and parse_rel read the replies
  correctly. The tagger works about as well as Qwen's (kept notes 99 / 107 vs 100 / 99 on nights 1 / 2), NREM dreams parse
  (560 paraphrases and 447 Q&A kept on night 2), and update checks answer both ways. So this is not a template or parsing bug.
  Suggested: K2-Horizon is a reasoning-only model, and with its thinking block closed at once it defaults to "no" on this
  yes-or-relation question. The bf16 arm never started (three hosts), so no bf16 data exists.

## Fixes (port only; Qwen runs unchanged, checked by the selftest)
1. **Memory:** K2 runs use 1,024-token micro-batches (`SLEEPB_TOK=1024`) instead of 2,048. Trainer.step sums each micro-batch's loss over the
   full batch's target count, so the loss and gradients are the same up to float summation order (checked by the existing split-path
   selftest). Also `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
2. **Names pass thinks briefly on K2:** for K2 only, each names question opens K2's low-effort thinking block (the template's
   `reasoning_effort="low"` generation prompt, `<ifm|think_faster>`). Stage 1 generates at most 256 thinking tokens, greedy, on the same
   base model, stopping at `</ifm|think_faster>` (or at the end of the turn). Stage 2 appends the thinking and a closing
   `</ifm|think_faster>` (added if stage 1 hit the cap) and generates the answer, greedy, at most 12 tokens, as before. The same
   `parse_rel`, `triple_status` and every later step are unchanged. Every other K2 prompt keeps thinking off.

## Abort rule (fixed now)
The bf16 run starts first. If its night-1 names pass still has yes = 0, the q4 run is not started, the bf16 run is stopped, and the result
is reported as "K2 never answers the names question". Otherwise the q4 run starts on the same code.

## Added to the report (not marks)
- Names pass per night: yes, new items, and the share of names-pass items that match a ground-truth fact (the run's
  eligibility diagnostics give precision among matched items).
- Thinking tokens per names question (mean), and the share of stage-1 generations that hit the 256-token cap.

## Compute
Coordinator OK (2026-10-25 13:46Z): K2 total cap $3.50; about $0.60 spent on the first try. Two RTX 5090 runs of about 2.5 h each.
