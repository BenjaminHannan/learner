# Loop-1L: think by looping (plus a latent board) instead of writing thoughts, on LFM2.5-24B-A2B (pre-registration, 2026-10-24 ~11:35Z)

Ben's v2 call (2026-10-24): the assistant should think by looping its middle layers and updating a latent space, not by written
chain of thought. On the 40 tau2 retail jobs, LFM2.5 with written thinking got 30/40 and with thinking off 23/40 (RESULTS-mac-lfm25.md).
Stage 1 on Qwen3.5-0.8B: the loop tied no-loop on validation (+0.4 over 3 seeds) and the lesion cost -7.7.

Model: LiquidAI/LFM2.5-24B-A2B (instruct), thinking off (assistant turn starts `<think></think>`), bf16, LoRA r16.
Data: backbone/assistant_data/data/train.jsonl (1,792 Claude-written tool-use chats); eval.jsonl (200 held out, never trained on).

## Arms (same data, same LoRA, same steps and seed list)
- A: LoRA, no loop.
- B: LoRA + loop: middle block (layers 16-23 of 40) run 4 times per forward pass, trained that way.
- C: B + latent board: each position carries a small latent state (d=256) that the looped block reads (added through a learned
  projection to the hidden state at the block's input) and rewrites after every pass (gated update from the block output).
  The board starts at a learned vector and is carried across the 4 passes only (not across tokens).
- Lesions (eval only): B and C run with 1 pass; C with the board zeroed. Test-time 8 passes reported for B and C (v1 found more
  passes at test time helped).

## Metrics
- M_tool (primary): on the 200 eval chats, for every assistant turn given the gold history, does the greedy reply make the same
  tool calls (same names, JSON-equal arguments, order-insensitive), or for a no-tool turn, does it make no call?
  Reported as % of assistant turns.
- Eval loss on assistant tokens (secondary).
- Speed cost: tokens/s relative to A.
- tau2 retail 40 (Phase 2, on Ben's Mac, one seed per arm, best seed by M_tool chosen only by M_tool): DB match /40.

## Seeds: 4 per arm (0-3). v1's lesson: don't judge on fewer.

## Marks (fixed now)
- K1 loop: mean M_tool B >= A + 2 points, and B > A in at least 3 of 4 paired seeds.
- K2 board: mean M_tool C >= B + 2 points, and C > B in at least 3 of 4 seeds.
- K3 jobs (Phase 2): the best looped arm >= 27/40 on tau2 with thinking off (closes over half of the 23 -> 30 gap), and >= A + 2.
**Wrong if** mean M_tool of both B and C <= A (looping adds nothing on the assistant task at this scale), or the 1-pass lesion
of B costs < 1 point (the loop isn't being used).
Budget: Phase 1 on one Vast A100/H100 80 GB, cap $3 (coordinator approval needed). Phase 2 on the Mac, free.
