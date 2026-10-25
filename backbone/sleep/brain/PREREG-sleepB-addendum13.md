# Sleep-B addendum 13: does a small whole-model sleep change survive a 4-bit model? (written 2026-10-25 ~16:10Z, before any addendum-13 code or run)

Labels: shown / suggested / untested. Same model (Qwen3.5-2B), Week-1 world, tests, scoring, seed (1), step schedule (AB stage 1,
`data/ab_schedule_stage1.json`) and open-book rehearsal as addendum 3. Not the village model, not the card experiments.

## Why
Ben (2026-10-25 13:49Z) asked what happened to "sleep that changes the whole model, but only just a little bit".
- **Shown (addendum 3, Week-1, one seed):** every LoRA-target weight trainable through an fp32 change at lr 5e-6 (ab_ob_full_s) gave
  recall 63.5 against the add-on control's 56, with ARC-Easy 92.4 (control 92.4) and diary 81 (control 82). At lr 2e-5 it broke
  general knowledge (ARC 82.2). 2x add-on work (66.5) later beat it, and it was never run on top of the adopted recipe.
- **The deployment problem (suggested):** both tiers run 4-bit (MLX affine, group 64, 16 levels per group). A small change to every
  weight moves most weights by much less than one 4-bit step, so it might round away when the model is re-quantized each morning.
  The add-on (LoRA) avoids this by staying 16-bit beside the 4-bit base.
- **Why it might survive anyway (suggested, untested):** the base weights sit at effectively random places inside their 4-bit
  bins. A shift d then changes about |d| / step of the codes, and the average change of the dequantized weight is d, as with
  stochastic rounding. The signal survives on average, with added rounding noise. Whether that noise is small enough is the question.
- One change at a time: before any whole-model arm on top of the adopted recipe (which is near its 94% recall ceiling on Week-2,
  so a gain could only show over several weeks), test the risk that would rule the idea out for deployment.

## Arm (Week-1, 1x work, seed 1)
- **ab_ob_full_s with `--q4-eval`:** training is exactly addendum 3's ab_ob_full_s (fp32 delta on every LoRA-target Linear, lr 5e-6,
  LoRA frozen, KL guard, full-rank SHY, morning gate). The only change: after the usual final scoring, the same final model is also
  scored under three 4-bit conditions. Each condition starts from the final model's weights and they are restored bit for bit after it.
  - **F (as scored now):** bf16 base + fp32 delta (the arm's own result).
  - **Q (morning re-quantize):** every Linear and Embedding fake-quantized to MLX affine 4-bit, group 64 (q4_apply, the code used by
    `--q4-base`), after folding the delta into each target weight in fp32 (W + delta). Delta hooks off.
  - **Qf (frozen grid):** as Q, but each group keeps the 4-bit scale and bias of the base weight W, and only the codes are re-rounded
    from W + delta (clamped to 0..15). Tensors with no delta are exactly as in Q0.
  - **Q0 (no sleep change, 4-bit):** W alone, fake-quantized the same way, delta off (the 4-bit model before any night).
  - **F0 (no sleep change, bf16):** W alone, delta off, no 4-bit.
- Each condition is scored on the weights-only memory questions (forward, reverse, two-hop, changed, routine) and on ARC-Easy (500).

## Pass marks (fixed now)
Let gain(X) = recall C2+C4 of X minus that of its own no-change model (Q - Q0 for 4-bit, F - F0 for bf16).
- **No harm (4-bit):** ARC-Easy(Q) >= ARC-Easy(Q0) - 3.
- **S1 (the small whole-model change survives re-quantization):** retained share rho = gain(Q) / gain(F) >= 0.75.
  **Wrong if** rho < 0.25: the change mostly rounds away, and a whole-model sleep for the 4-bit tiers would need
  quantization-aware training or a kept 16-bit change (which is an add-on again).
- If gain(F) < 20 points the run does not replicate addendum 3 and S1 is not judged.
- **Reported, not marked:** rho for Qf; recall, reverse, two-hop, diary in every condition; the share of 4-bit codes that differ
  between Q0 and Q and between Q0 and Qf, and the mean |delta| divided by the group's step (scale), per module type; F vs addendum
  3's 63.5 (replication; a gap under 4 points is seed-level noise).
- **Expectation (not a mark):** rho 0.5 to 1.0; codes changed 5-30%; Qf at least as good as Q.

## What comes next (not part of this test)
If S1 passes, the next arm puts the whole-model change on top of the adopted recipe over several weeks (nightly add-on, plus a slow
whole-model change, compared with the add-on alone, judged on recall of week-1 facts in week 3), sealed separately. If S1 fails,
the next test is quantization-aware training of the nightly change. Neither is preregistered here.

## Compute
The fp32 change, its gradient and AdamW state need more than 30 GB (addendum 3), so one 80 GB-class GPU on Vast: about 1 h with the
extra scoring, about $1.00-1.30. Rental needs the coordinator's OK under this week's $30 cap. A box that is not running within
10 minutes is dropped. The JSON is pulled after the self-stop, and only then is the box destroyed.
