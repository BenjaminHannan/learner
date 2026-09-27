# Feedback-written patches: local experiment

Created 2026-09-27T22:10:26Z (from `date -u`).
Base: `3b15a8cce8ca16e0a1b070d039e3ac745b633783`.

Status: implementation and qualification, not a race result. All proposed benefits are **untested**.

Only this directory and new `scripts/claude_patch_*.py` files belong to this experiment.
No changes enter Ben's main model. Existing ledger work was preserved after the initial
pull's autostash conflict; the autostash remains available.

## Order and seals

1. Implement the no-kind-label loop, plain control, and rank-eight patch net.
2. Run numerical construction checks in fp32, without autocast.
3. Seal the candidate generator sources, candidate kinds, development panels,
   qualification budget, and episode recipe **before any optimizer training**.
4. Train one separate loop pilot to qualify the candidate kinds. It is not a race control.
   Required sums and grids must each score at least 285 of 300. Every extra kind
   must score at least 270 of 300. Drop failed extras before the final practice seal;
   never change these thresholds. If fewer than four extras qualify, practice
   eligibility is not established and no race may start.
5. Seal the qualified list before training the independent two-seed arms.
6. Train and check every arm on that same list. The patch must also be within
   nine of 300 of both paired loop controls on each old kind.
7. Only run the race after the test chat's protocol and RACE-PASSMARKS are on main,
   and after committing ADDENDUM-wide-practice.md. The addendum cannot be finalized
   against an absent protocol. Do not use the GPT proposal as a substitute for it.

The initial pulled main has neither test-chat protocol nor race marks. If practice
finishes first, publish the construction/qualification report and stop as requested.

## Local runtime

PyTorch 2.14.0 and NumPy 2.5.3 were found in the existing uv cache. The command
`uv run --offline --no-project --python python3.12 --with torch --with numpy python -B`
uses cached packages only. Apple MPS is available. Use fp32 on MPS, no autocast,
no rentals, no downloads. Record actual timings; do not extrapolate a result.

## Accounting and claims

Count all trainable parameters and 4,096 persistent A/B coefficients. Report
raw replay storage separately and keep allowances equal. Counts in final reports
use 'x of 300'. Construction checks do not establish learning or transfer.
A separate Sol subagent will recount final key numbers from raw files and marks,
without reading the lead's verdict first.
