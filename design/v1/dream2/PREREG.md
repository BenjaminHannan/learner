# Dream2 creative-sleep A/B (pre-registration, written 2026-10-23 ~20:00Z BEFORE any run)

Research report item R3: https://claude.ai/artifact/JnL9CRkskZksidFTK7EiQZ

## Setup (both arms identical except the one change)
Creative module only (no D): B2_s200 parent (sha256 94057436...), bridge zero (P_dc = 0, as in Gate S's sleep trial), G1 on
(K-FAC lock + KL 30, v1/g1.py), C2b sleep recipe of v1/creative_sleep.py, FULL pool (1,024), seed 0, same box type (RTX 4090).
Scoring: creative dev (256 rows; by kind ~51 each), greedy first try, official scorer. Sealed test.jsonl never read.

## The one change
TREAT: `--dream2 256 --dream2-max-steps 4` (256 random 1-4-step B2 programs, labelled by execution, added to each night's
records; creative/dream2.py). CONTROL: `--dream2 0` (today's behaviour).
Why 4 steps: in B2's executor affine takes 3-5 steps, double_add 2-3, sq_plus 3-4 (C2 manifest), so 2-step dreams cannot
contain them.

## Marks (fixed now)
- P1 (main): TREAT's mean first-try over the three hard kinds (affine, double_add, sq_plus) >= 15% AND >= CONTROL's + 10 points.
- P2 (no harm): last_digit and square each drop no more than 5 points vs CONTROL.
- Proves wrong: TREAT's hard-kind mean < 5%, or < CONTROL's + 3 points.
- Disclosure, reported not gated: creative/dream2.kind_overlap on the dreams actually used (share functionally equal to each
  held-out kind's form). If the hard-kind gain comes only with high overlap, it is "taught the form", not discovery.
- Single seed; n ~51 per kind, so a difference under ~10 points is within noise.

## Budget
Two Vast boxes in parallel, cap $3 each.
