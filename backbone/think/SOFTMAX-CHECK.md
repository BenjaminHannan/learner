# Softmax Collapse / Cancellation check (Barron, Gnanapragasam & Tschannen, arXiv 2610.31642), 2026-10-24

CPU only (torch 2.14.1). Numbers: `softmax_reach.py` -> `softmax_reach.json`; tests: `test_kl_guard.py` (K1-K3), `test_xent.py` (X1-X4).
Fixed losses: `xent.py` (copied unchanged from Ben's Think-1 branch) and `xent_reverse.py` (new: reverse KL, rlaif's direction).

## Verdict

| Place | Bug reachable? | Does it matter? | Change |
|---|---|---|---|
| sleep1.py `F.kl_div` guard (branch j59yy5) | Yes: a fresh LoRA (B = 0) makes cur == ref bitwise at the first step of a night [shown, K1] | No. Residual on LoRA B 6.6e-7 vs the CE gradient 0.14-0.66 on the same batch; it changes the combined Adam step by 2e-7 of its size (R1, R2, R4). KL-only Adam from B = 0 drifts B by at most 2e-6 after 100 steps at lr 1e-4, because the real KL pulls it back (R3) [shown, toy] | None needed; `fixed_kl(cur, ref, reduction="sum") / n` is a drop-in for future runs |
| sleepb.py KL guard + `ab_klctx` leash (branch cqc4bi, lines 454, 474) | Yes, same case | No, same reason: the KL is always summed with a CE term before one Adam step | Same drop-in |
| rlaif rollout.py `_lp_kl` (branch j5hhcz) | Not in practice. The two views always differ (critique/hint vs none), so logits are never equal. Even the smallest possible difference (bf16 rounding of the hidden state) gives a real gradient 1.1e-3, 1,700x the 6.6e-7 residual; standard and fixed agree to 1.5e-4 relative (R5) [shown, toy] | No | None; `fixed_reverse_kl` is ready if wanted |
| Hard-label CE (sleep1, sleepb, loop1l.py, backbone/train.py, rlaif `_lp`) | Collapse needs margin > 16.6 in fp32. Every active CE/log-softmax casts logits to fp32 first; no bf16 CE found outside `archive/`, `design/pilots/`, `memorylab/` (those are fp32 CPU or old) [shown, grep] | No: at that margin the true per-token gradient is below 6e-8 anyway | None |

So no published number changes and no rerun is needed. The live RLAIF Kaggle run is unaffected.

## Caveats
- The toy is a LoRA head on random weights with Qwen3's vocab (151,936), median top prob 0.31. A real model's residual scales the same way (about q * 1e-7 per logit) [suggested].
- Not checked: the MLX sleep port (`sleep1_mlx.py`); MLX reductions differ, but the KL there is also summed with CE [untested].
