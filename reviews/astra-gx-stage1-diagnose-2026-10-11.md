# Prompt for Astra: why did the experts model (GX) lose? (2026-10-11)

You can read this repo. This is a diagnosis task only: **do not edit files, train, run tests, or use any GPU.** Read, reason, and answer.

## What to read
- Spec, marks and result: `design/8a-gx-experts-2026-10-09.md`. Read section 2 (the change), section 4 (stage 1 marks), addendum A
  (even-use mark X4 and the balancing nudge), addendum C (memory and checkpointing), addendum G (the rented-box plan) and addendum H
  (the result).
- Code: `custom_io/models/` (the ledger model's MoE layer: search for `experts`, `top_k`, `moe_lb`, the balancing bias) and
  `custom_io/g8a/analyze_gx.py` (how X1-X4 are computed, including the routing report).
- Results: `custom_io/results/gx-box/50-gx-s400` and `51-gx-s401`. Each has `8aGX-3M-sNNN/B2/RESULT.json` (GX) and
  `8aG1d|8aG1e-3M-sNNN/B2/RESULT.json` (the same-box control with experts off). The training lines are in `tick-gx/stdout.events.txt`
  and `tick-ctl/stdout.events.txt`. The scored summary is `analyze_gx-stage1.json`.

## The result (shown)
GX swaps the small thinker's feed-forward layers for 52 experts, with 8 picked per token. It has the same work per question and 3x the
trained parameters (10.55M against 3.54M). On the same machine and seed it scored lower than the experts-off twin on both seeds
(pooled-5: 70.93 against 72.55, and 72.05 against 73.25; mean -1.41). It lost most on the rule families: seq_next 36 against 51,
rule_apply 45 against 62.5, cipher_map 66 against 80. On dev question rows, expert use was uneven (2-4 unused experts per block, the
busiest at about 4x an even share), so X4 failed. In training on the mixed rows (38% questions, 62% web fill-in), the log's busiest
and least-used shares ended at about 1.3-1.4x and 0.66-0.77x even.

## Questions
1. Which explanation does the evidence support best? (a) Experts do not help this looped thinker at this size. (b) The experts
   specialised by kind of row, so question rows reach only a subset, and those carry fewer parameters than the dense twin's layer.
   (c) Optimisation or setup: learning rate, the balance loss weight 0.01, the bias nudge 0.001 applied per micro-batch pass (4 per
   update), checkpointed recompute, init. (d) Something else in the code. Check claims against the code and logs.
2. Is X4, measured on dev question rows only, the right test for Ben's "used about evenly"? Or should it be measured on the training
   mix? Answer without changing the result already recorded.
3. If one follow-up is worth running, name ONE change, with pass marks fixed in advance and the result that would prove it wrong. If
   none is worth the GPU time, say so.

## Rules for your answer
- Label every claim **shown** (you checked it in code or results), **suggested** (reasoned but not checked) or **untested**.
- Keep the small card experiments (this 3M test) and the village model separate. Do not carry conclusions from one to the other
  without saying so.
- One change at a time, marks before any run.
- End with a plain-language summary for Ben (a high-school senior): a few short sentences and no jargon.
