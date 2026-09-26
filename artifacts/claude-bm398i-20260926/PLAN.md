# bm-398i PLAN: adapter on/off switch and isolation (benchmarks thread, 2026-09-26 ~13:55 UTC)

Registered and sealed before the scored run. Before sealing, a 2-items-per-kind timing run (6 items, 609 s, not
scored) set the item counts, and the selftest passed 9/9. Counts only: no question, answer or reply is quoted.

## Why
bm-397t's short-answer LoRA was merged into the weights, so it changed every answer, and GSM8K fell from 191 to 42.
The outside review (reviews/outside-review-bm397t-2026-09-26.md) asked for its first step to be this: keep the
base frozen and the adapter unmerged, with an explicit bypass. Pass means disabling it reproduces the base, and
switching between requests does not change later answers.

Split agreed with Month-end at 12:50 UTC:
- Benchmarks builds this switch and this test.
- Month-end owns the router ("needs memory?", "needs calculation?") after 383's verdict, then bm-397m, which turns
  the adapter on for the memory path only.

## The one change
Each q/k/v/o projection of the plain MiniCPM5-1B (96 of them) is wrapped in a switch holding bm-397t's LoRA shape:
rank 16, alpha 32, fp32 A and B, with the same math as claude_blurt2.add_lora in eval mode.
- Off: the switch returns the base projection's own output, with the adapter not added at all.
- On: base + scale·x·Aᵀ·Bᵀ.
- Nothing is merged and nothing is trained.

## Adapter
A fixed-seed random nonzero adapter: seed 3989, A kaiming-uniform (as claude_blurt2), B normal with std 0.02.
The mechanism doesn't depend on what the adapter learned, so this runs at $0 on this CPU. A confirmation with the
real bm-397t adapter (--adapter PATH) follows on BensPC as its own run, with the same marks.

## Items and settings
- 15 GSM8K, 40 MMLU and 20 LoCoMo, 75 in all:
  - GSM8K and MMLU are the first items of bm-390's GSM8K-300 and MMLU-300, with bm-390's prompts and token limits
    (512 and 16).
  - LoCoMo is the first 20 of bm-398d's sample, laid out from E20's lines as in bm-395, with 50 tokens.
- Greedy, thinking off, claude_bm390.generate, CPU fp32, one process.
- Four passes:
  - base: unwrapped;
  - off: wrapped, adapter off;
  - on: adapter on;
  - mixed: every item once in each mode. On and off alternate between requests (on-order and off-order each
    shuffled with random.Random(3988)), so every request follows a switch.
- The last-position logits of the first 3 items of each kind are compared exactly: base vs off, base vs off again
  after mixing, and base vs on.

## Marks (fixed now; coded in run())
- **I1 (off is the base):** all 75 off replies are byte-identical to base, and the logit difference is exactly 0.0.
- **I2 (switching leaves no trace):**
  - all 75 mixed-off replies are byte-identical to base;
  - all 75 mixed-on replies are byte-identical to the on pass;
  - after mixing, the off logits differ from base by exactly 0.0.
- **I3 (the test is not empty):** the adapter changes at least 20% of the replies (on vs base). If not, the verdict is
  INCONCLUSIVE, whatever I1 and I2 say.
- **PASS** = I1 and I2 with I3 holding. **Proved wrong:** any off or mixed-off reply differs from base.

## Predictions
- P1 (95%): PASS.
- P2 (90%): I3 holds with at least 60 of 75 replies changed. The timing run's 6 of 6 changed replies are not
  scored.

## What it leads to
- PASS: the switch is ready for bm-397m inside Month-end's agent, once the router exists, and for any later
  adapter. It shows only that switching can't harm the base. It says nothing about whether an adapter helps.
- FAIL: find the leak (state, caching, dtype) before any adapter is routed.

## Files
- scripts/claude_bm398i_switch.py (selftest 9/9: off equals the base exactly; on equals bm-397t's LoRA; a saved
  bm-397t adapter file loads with every key).
- The run writes replies to the scratchpad; the repository gets result.json (counts only) and RESULTS.md.
