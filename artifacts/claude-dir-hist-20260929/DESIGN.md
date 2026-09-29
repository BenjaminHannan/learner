# History read: letting each round see all its earlier states

## What Huginn does and what our loop already does (checked against code, scripts/claude_fewex_net.py)
| Huginn idea (Geiping et al. 2025, arXiv 2502.05171, read for this page) | Our loop today | So |
|---|---|---|
| Feed the prompt embedding into every round (concatenate with the state, then a learned adapter) | Already: `step` computes `LN(blocks(h + e))` every round (net.py:77-81), with `e` the prompt. It is added, not concatenated. | Nothing to test for Ben's first idea; it exists. A concat+adapter form is a possible later tweak (Huginn says concat works better at scale; untested here). |
| Start the state from random noise | Start is zeros (net.py:105, 121, 135). | Not present. Zero-training read is inside S2 (it compares two starts). Training with a random start is a later single-change test. |
| Random number of rounds in training, backprop only through the last few | Already: total ~ uniform 1..16, gradient through the last k ~ uniform 1..min(total, 6) (net.py:165-166); tested up to 48. Huginn uses a log-normal Poisson, mean 32, k = 8. | Same idea, different distribution. |
| Stop when the output stops changing between rounds (KL under 5e-4) | Learned stop head, capped at 48; no convergence rule. | Zero-training read already planned as S2 "Watch it think" (CONVERGES / DRIFTS). Pond, H12 and Stop-without-labels train the stop. Nothing new to add here except, optionally, a KL column in S2. |
| Each round reads all earlier states | No: a round sees only the previous state and the prompt. | **Ben's question. This test.** (Huginn itself does not do this either: it only warm-starts from the last state, and caches a fixed number of recurrent KV entries.) |

## The test
One change: `h_new = LN(blocks(h + e + R))`, where R is a learned single-head attention, per cell, over that cell's last 8 states (queries and keys 64-wide, value = the state, output matrix zero at start, so the net starts as the loop). The window is a fixed ring, so a 48-round test never sees more entries than a 16-round practice round (Huginn does the same with a fixed cache budget).
Cost: +98,688 weights (+6.0%), 8 extra states held per cell (81 cells, width 256: small). Cheapest faithful version: an all-history attention grows with rounds and changes shape between practice (up to 16) and test (48), so the fixed window is the cheap fix. A running average of states (one 256x256 matrix, +4%) would be cheaper still but blurs the states together; kept as a fallback if the attention version does nothing.
**Control that stops extra size taking the credit:** CTRL-W1, same read layer with window 1: it sees only the previous state. It has the same weights and compute. If HIST beats it, the gain comes from the earlier states.
**Why it might help (suggested, untested):** the loop must currently keep everything it needs inside one state; seeing earlier states lets it notice a cell that flipped, compare guesses across rounds, and back out. **Why it might not:** on mazes the state already carries the previous guess, and a plain deeper loop may be all that is needed.
Cost of the test: 4 practice runs (about 3 hours each on Mac CPU at 2 threads by the H3 timings; untested at this size) and 4 dev ladders (about 3 hours). $0. Odds of passing all three marks in both seeds: my guess 1 in 6.
