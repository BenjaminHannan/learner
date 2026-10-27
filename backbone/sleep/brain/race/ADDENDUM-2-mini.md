# Race-mini addendum 2 (2026-10-27 ~20:40Z; before any LFM3 run, both sides)

Ben (19:45Z Oct 27) moved the small tier from K2-Horizon-3.7B to LiquidAI/LFM3-1.7B. Racing on a model we won't ship wastes the PC slot, so race-mini
round 1 moves to LFM3 before it runs. Everything in PROTOCOL-mini and addendum 1 holds except:

1. **Model and served base.** LiquidAI/LFM3-1.7B at rev 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd. The frozen base is the file the Mac serves
   (llama.cpp): LFM3-1.7B-QAD-Q4_0.gguf from LiquidAI/LFM3-1.7B-GGUF at rev b3f2ae5d73cd3c91bf40e8ba752c648aa05dffdf, loaded dequantized
   (sleepb --q4-gguf, add-on side's commit 267fa0598). All 153 Linears are Q4_0 (group 32, one fp16 scale, no offset), the tied embedding Q6_K, norms/conv F32.
   Both sides train on top of exactly this base in bf16 (bf16 cast rel error ~1.7e-3). Chat: ChatML, thinking off (`<think></think>`).
2. **Whole-model storage in Q4_0 form.** Q4_0 has no offset, so qs trains only the per-block scale: S = s0 (1 + u), stored B = -8 S, change s0 u (q - 8);
   codes read back from the base (they re-quantize exactly with q40_quant, checked against gguf-py). Morning: u x0.85, S rounded to fp16 (nearest).
   s0 is the bf16 value of the GGUF's fp16 scale (rel error <= 2^-9); that only matters for writing the served file, not for the race.
   The lr scout ladder (1e-3, 3e-3, 1e-2) and pick rule are unchanged.
3. **Add-on storage:** LoRA r16 a32 on q/k/v/o_proj, conv.in_proj/out_proj, feed_forward.w1/w2/w3 (16.1M params), served at runtime (llama.cpp --lora).
4. **Validity:** the dose gate of addendum 1, rerun on LFM3 (lora_s1 at 300 steps vs c75_s1 at 75, seed 1, gap >= 2 or stop). Reported only, never a gate:
   bf16c75_s1, the add-on at 75 steps on the bf16 safetensors base (what the served Q4_0 base costs the add-on).
5. **Out dir** fresh (~/race-mini/out-lfm3); the K2 lora_s1 is kept as K2 history only.
6. Score and pass marks unchanged (C2+C4, 75-step control c75, ceiling fallback decided from c75 alone first, McNemar on the pooled 400, harm ARC-500 >= base - 5).
   Substring scoring is kept; the served base sometimes writes "...</think>answer", which counts the same for every arm.

Code: race_mini.py --base q4_0 (default --q4-gguf = the file above, downloaded once), pc_race_mini.sh (RM_MODEL default = LFM3 + q4_0). Run order:
lora_s1 (300), c75_s1, gate, c75_s2, CEILING DECISION, lp16_s1, scout_qs x3 (Week-1, 3 nights), qs_s1, lp16_s2, qs_s2, bf16c75_s1. Needs `pip install gguf` in ~/bbvenv.
