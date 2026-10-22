# How the sparse MoE core would take Huginn's ideas (plan only, not part of the sealed test)
Written 2026-09-29 by the MoE owner thread. Nothing here edits a sealed file or changes mxd-1..4.

## What the code already does (shown, by reading claude_fewex_net.py:77-81, which the MoE net reuses)
Each round computes z = h + e, where e is the embedded prompt, then runs the layers, then a LayerNorm.
So the prompt is already added into every round. Idea 1 ("feed the prompt every round") is partly in.
What Huginn does differently (suggested, from the Learn-from-Huginn thread's summary): it joins the prompt to the state
and mixes them with a learned adapter instead of adding them. Untested here whether that beats plain addition.

## Idea 1 variant: concat + adapter injection (new, small)
- Change: replace z = h + e by z = W[h ; e] (a d x 2d linear, init near [I, I]/2 so round 1 matches today).
- Owner: a new addendum plug-in file (own prefix), not an edit of claude_moe_deep_net.py.
- Experts unaffected: the adapter sits before layer 1 of each round, so routing sees the same width d.

## Idea 2: access to previous states (new)
- Change: each round also attends to a short memory of earlier round states (e.g. every 4th round's h, capped at 8 slots).
- With MoE: the memory only feeds attention, not the router, so routing stays per-cell. Cost: extra keys in attention only.
- Risk (suggested): more state to read may let the net skip using rounds well; check stop failures in the report.

## Test order (one change at a time, after the sealed run reports)
1. Sealed MoE-deep (mxd-1..4) reports its verdict first. If PROVED WRONG, neither idea is layered on it; go back to the dense loop.
2. If PASS or NOT SHOWN with healthy routing: run Idea 1 variant alone. Pass mark fixed in advance: F_eq at least +8.0 over the
   sealed MoE row in both seeds (8.0 is the F_eq noise bar in the repo), and F_few not worse than -10.5.
   Proved wrong if it is at or below the sealed row in both seeds.
3. Then Idea 2 alone, same marks. Only then both together.
Same-GPU loop control, plain-big row and routing-health rows stay required, per PASSMARKS.md.
Nothing is built until the Huginn thread says which of its own ideas passed.

---
# Follow-up tests from Ben (02:43 UTC 09-29): more experts, deep experts, non-transformer core
All are one-change tests that run only after the sealed run (mxd-1..4) reports. None touches the sealed test.
Common marks, fixed now: compare to the sealed MoE-deep row of the same seed and the same-GPU loop control.
UP = at least +8.0 F_eq over the sealed row in both seeds (8.0 = the F_eq noise bar in the repo). PROVED WRONG = at or below it in both seeds.
Anything else = NOT SHOWN. F_few must not fall more than 10.5 below the sealed row. Plain-big, dead-expert and stop-failure rows stay required.

## What is already known (by reading the code, shown)
- The sealed net's experts are already small MLPs (scripts/claude_moe_deep_net.py MoE class: w1, b1, w2, b2 per expert). MoE replaces only the
  feed-forward part of each layer; attention is the other part, and it is what lets one maze cell read other cells.
- mxd-3 already sweeps experts 16 / 32 / 64 / 128 at 8 layers and reports the curve as UP, DOWN, FLAT or MIXED.

## (a) A ton of experts (beyond 128, fine-grained)
Run after mxd-3's curve. Only if the curve is UP at 128, test 256 and 512 experts with the expert hidden width cut so active weights stay equal
(more, smaller experts). Untested: whether routing stays healthy (dead experts) and whether the batched-dispatch speed holds; the CPU timing
earlier was already 7x slower than the loop, so check TIMING first. If mxd-3's curve is FLAT or DOWN, skip it.

## (b) Deep experts (each expert is a small multi-layer MLP)
Change: each expert has 2 hidden layers instead of 1, hidden width cut so total stored weights match the sealed row. Layers stay 8.
Untested guess: depth inside experts and depth across layers overlap, so the gain may be small; the mxd-3 depth curve (2/4/8/16 layers) says
whether depth helps at all. Run only if depth-at-64-experts is UP.

## (c) Non-transformer core: APPROVED as a comparison (Ben 02:44:33 UTC: yes; attention core stays the main line)
Compute: Ben allows vast for this MoE work (02:44 UTC). Cheapest box that does the job; send the cost to the channel session before any single spend of $0.50 or more; destroy a rental only after a checked copy-back. (MLP experts + cheap cross-position mixing, MLP-Mixer style)
Answer for Ben (suggested, not shown): the experts can be plain MLPs, but a net with no mixing across positions cannot pass information between
maze cells, and a maze answer needs that. So the core needs some cross-cell mixing; attention is one way, a mixer layer (an MLP across positions)
is another. A mixer needs a fixed number of positions; check that against maze sizes before building (untested).
Change: swap attention for a mixing MLP across cells, keep MoE experts and the loop. Same weight count. This is a real design change, so it
needs Ben's word on architecture before any GPU time (the 00:35 approval covers MoE and layers, not a new core).

## (d) Each previous loop state as input
Not duplicated here: it is Idea 2 above and belongs to the Learn-from-Huginn thread. I will plan how the MoE core takes it once that thread says it passed.
Order after the sealed run: Idea 1 variant, (a) if mxd-3 says UP, (b) if depth is UP, Idea 2, (c) as a comparison against the attention core.
