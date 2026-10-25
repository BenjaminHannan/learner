# Sleep-B addendum 12: the sleep recipe on the big tier, Qwen3.6-35B-A3B with a 4-bit base (written 2026-10-25 ~15:25Z, before any addendum-12 code or run)

Labels: shown / suggested / untested. Week-2 world (sha256 70db7146...), tests and scoring as addendum 9. Not the village model, not the
card experiments.

## Why
Ben (2026-10-25 13:40Z) chose Qwen3.6-35B-A3B as the big-tier backbone ("go with Qwen 3.6"), replacing K2-Horizon-MoVA-36B. Earlier (12:36Z,
12:40Z) he asked for sleep on the big model's q4 version only. The adopted recipe ab_ob_b4_nb gave recall 91.5 / 91.0 and two-hop
38.5 / 35.9 on Qwen3.5-2B in bf16. This is a transfer test, not a tuned run.

## Model
Qwen/Qwen3.6-35B-A3B, revision 995ad96eacd98c81ed38be0c5b274b04031597b0, loaded text-only as Qwen3_5MoeForCausalLM (shown in the bench: all
language weights load, 34.66B parameters, 64.6 GiB in bf16). 40 layers (30 Gated DeltaNet + 10 full attention), 256 routed experts (top 8)
plus one shared expert per layer. Thinking off with the template's `enable_thinking=False`, as for Qwen3.5-2B.

## Arm (Week-2, work scale 4, seed 1)
- **q36_q4:** ab_ob_b4_nb, everything as on Qwen3.5-2B, except:
  - **4-bit base:** `--q4-base --q4-mlx-moe`: an MLX-affine quantize-dequantize copy of the published mlx-community 4-bit config
    (4 bits, group 64, on every Linear and Embedding and on the fused 3-D routed-expert tensors; 8 bits, group 64, on every router
    `mlp.gate` and `mlp.shared_expert_gate`). Weights stay bf16 in GPU memory. The routed experts are frozen.
  - **LoRA targets:** the same rank, alpha and names as for Qwen3.5-2B (full-attention q/k/v/o and Gated DeltaNet in_proj_qkv/z/a/b and
    out_proj), plus the shared expert's gate/up/down_proj, which is this model's only dense MLP (on the 2B every MLP takes LoRA; the
    routed experts here are fused 3-D tensors that standard LoRA cannot target). 310 modules, 21.2M trainable parameters (bench).
  - Everything else (steps, dreams, names pass, bridge prompt, KL guard, SHY, gate, gen batch 32, 2,048-token micro-batches) unchanged.

## Pass marks (fixed now)
- **No harm:** ARC-Easy >= the same model's pre-sleep ARC-Easy (`--arc-base`, the same 500 questions, on the 4-bit base) - 5, and diary
  pooled >= the same model's `base_diary` - 5.
- **B1 (the recipe transfers to the big tier on a 4-bit base):** recall on C2+C4 >= 75.
  **Wrong if** the tagger's mention recall is >= 0.5 and the names pass answers yes to at least 20% of its questions, but recall is < 60:
  then note-taking works and the learning does not transfer.
- **Reported, not marked:** two-hop, reverse, changed-new, routine; tagger recall and precision; names-pass counts; chain yield; reverts;
  q36_q4 vs Qwen3.5-2B ab_ob_b4_nb seed 1 (paired on the same questions); wall time and dollars against the bench estimate (4.4-4.6 h).
- **Expectation (not a mark):** recall 75-90 (a larger and better model, but a 4-bit base and LoRA that misses the routed experts);
  two-hop 30-50.

## Compute
One RTX PRO 6000 (95 GB) on Vast, about 4.6 h plus a 10-minute download, about $5.50-6.00 at $1.20/h (bench, 2026-10-25 15:16Z, results in
`results_a11/`). Coordinator OK 2026-10-25 15:17Z, cap $6.50. A box that is not running within 10 minutes is dropped. The JSON
is pulled after the self-stop, and only then is the box destroyed.
