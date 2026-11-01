# Race-mini round 1 on LFM3-1.7B (served QAD-Q4_0 base): result (analysed 2026-11-01 ~18:15Z)

Run: BensPC RTX 5070 Ti, 2026-10-31 ~08:50-12:03Z, commit 49f7432 (= frozen round-1 code f5d5bc5f81 + the two start-up fixes, preflight and waiter changes; no arm, scoring or seal changed). Every run rc=0. Raw files: this folder.

## Gates fixed in advance
- Preflight (pf_lora / pf_lp16 / pf_qs / pf_bf16): all passed.
- Validity (addendum 1, dose): 300-step lora_s1 final C2+C4 0.97 vs 75-step c75_s1 0.165, gap +80.5 points (pass needs >= 2). PASS.
- Ceiling decision (from c75 alone, logged before any treatment arm): pooled c75 final C2+C4 = 0.2075 < 0.90, so the headline stays FINAL.
- Whole-model lr scout (Week-1, 3 nights, ARC-100 drop <= 3): 1e-3 0.225 / ARC 0.83; 3e-3 0.3375 / 0.81; 1e-2 0.3625 / 0.59 (fails the ARC rule). Picked 3e-3.

## Headline: forward recall C2+C4, final night, pooled 400 items (2 seeds x 200), paired exact McNemar
| arm | seed 1 | seed 2 | pooled | vs c75 | p | ARC-500 (s1 / s2) | held-out KL |
|---|---|---|---|---|---|---|---|
| c75 (add-on control, LoRA r16, lr 2e-4) | 16.5 | 25.0 | 20.8 | - | - | 82.4 / 83.4 | 0.050 / 0.046 |
| qs (whole-model: Q4_0 scales, lr 3e-3) | 77.5 | 74.5 | **76.0** | **+55.2** (225 vs 4) | 2.6e-61 | 84.6 / 84.6 | 0.40 / 0.32 |
| lp16 (add-on: LoRA+ x16) | 74.0 | 69.0 | 71.5 | +50.7 (211 vs 8) | 2.8e-52 | **42.8 / 32.2** | 1.94 / 1.61 |
| bf16c75_s1 (reported only: add-on on the bf16 base) | 19.0 | - | - | - | - | 83.2 (bf16 base 71.4) | 0.071 |
Base ARC-500 on the served Q4_0 base: 72.2. Head to head, qs vs lp16 pooled: +4.5 (46 vs 28), p = 0.047.
Per-seed direction vs c75: qs +61.0 / +49.5, lp16 +57.5 / +44.0. Other rows (s1/s2): qs changed-new 0.77/0.90, routine 0.95/0.80; lp16 changed-new 0.77/0.80, routine 0.85/0.80; c75 0.13/0.30 and 0.15/0.30. C1 stays 0 everywhere; two-hop ~0 everywhere.

## Verdicts by the sealed PREREGs
- **Whole-model round 1 (qs): PASS** - pooled >= c75 + 4 (+55.2), p < 0.05, same direction on both seeds, no harm (ARC 84.6 vs base 72.2 and vs c75 ~83).
- **Add-on round 1 (LoRA+ x16): FAILS on harm** - recall +50.7 (p < 0.05) but ARC-500 fell to 42.8 / 32.2 (base 72.2; harm = below base - 5). Held-out KL ~35x the control's.

## Caveats (labelled)
- Shown: ARC rises from 72.2 (base) to ~83 after only 75 steps of fact training in EVERY arm, LoRA control included. The ARC scorer reads the letter logits right after the chat prompt, so the base is likely penalised for formatting (it wants to write something else first), not for knowledge. The control (~83) is the fairer harm reference; both verdicts are unchanged under it.
- Suggested: the comparison favours qs on tuning. qs got an lr scout (3e-3 picked); the LoRA control kept the 300-step lr 2e-4, under which it learns slowly at 75 steps (20.8). LoRA+ shows faster LoRA learning is possible but here it broke general ability. An add-on lr scout at 75 steps is the obvious fair next step for that side.
- Shown: qs trains 45.8M scale numbers vs 16.1M LoRA numbers, at the same steps and data; qs wall time ~850 s vs ~450 s per run.
- Shown: qs drifts more than the control on held-out text (KL 0.32-0.40 vs 0.05) without ARC harm.
- Untested: Week-3 held-out, diary, and whether the qs gain survives writing the scales back into the GGUF (fp16 rounding is applied each morning in training, so it should).
