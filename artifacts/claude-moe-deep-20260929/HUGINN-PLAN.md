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
