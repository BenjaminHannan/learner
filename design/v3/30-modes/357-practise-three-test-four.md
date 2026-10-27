# 357: practise three-step, test four-step (road map R7)

Sleep research thread, 2026-09-25 04:50 UTC. Ben: "get as much done by morning".

## Why
rsn-355 (registered FAIL): with the shared chain-step input the full-size plain net still gets 0/30 on
never-practised three-step, even raw. CPU previews (PREVIEW.md) found the same pattern for the loop: at
most a little raw three-step, almost nothing that passes the fact-check (which needs every row of the chain
cited), and more rounds don't help. rsn-355's own "next step" was to practise three-step (round 1's C1).
The shared input makes one more thing possible: room for a fourth step (MAX_HOPS 4; the old input had a
fixed slot per step). So three-step becomes practised, and four-step becomes the "past practice" test.

## The one change (scripts/claude_rsn357_run.py)
Three-step joins practice (value3 replaces 1 in 8 practice puzzles). Base = rsn-355's shared input with 4
step positions. Everything else is 296's recipe. Two arms, 2 seeds each:
- plain: 296's plain net
- loop: the loop net with rsn-353's fix (no per-pass step embedding); 12 rounds at evaluation

Test (scripts/claude_rsn357_four.py): 300 code-made four-step questions (296's generator, seed 5151,
re-solved by the independent solver), never practised. Code-made, so they share the generator's style;
they test depth, not wording. Panel296's three-step category is now PRACTISED: it is reported, never
quoted as a gain in reasoning (Ben's rule: no targeted practice counted as intelligence).
Deviation as in 355/356: BensPC is Windows, so --workers 0.
