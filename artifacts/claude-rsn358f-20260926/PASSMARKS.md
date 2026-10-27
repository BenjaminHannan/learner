# rsn-358f pass marks (fixed before any run; sleep research thread, 2026-09-26, after 11:00 UTC)

Question: trained as a LOOPED FLOW (each round denoises a noisy copy of the answer whose noise falls round by round,
state carried forward), does the 358a loop beat its plain same-size twin on BIGGER puzzles than it practised?
Source: "Thinking with Looped Flows", arXiv 2609.11801 (claims checked against the full text,
/mnt/project-files/research-2026-09-26/papers/2609.11801.txt: sorted t ~ U[0,1], shared x0/x1 across steps, loss at
every step with stop-gradient between steps, sigma = 1/sqrt(|V|), halt head weight 0.5 not used to stop at test,
~0.27M extra input weights; Sudoku-Extreme 97.9 +/- 0.4; 74.5% at 8 steps -> 97.9% at 128).
Code: scripts/claude_rsn358f_flow.py (docstring lists exactly what is and is not copied from the paper).
ONE change vs the 358a loop arm: the looped-flow objective and inference as one package; width trimmed 512 -> 496 so
weights match plain within 2% (flow 6,356,158 vs plain 6,385,149). Data stream, steps (60,000), batch (256), lr,
schedule, seeds 1 and 2, and the sealed tests (artifacts/claude-rsn358a-20260925/tests/, run once per new checkpoint)
are 358a's. The plain arm is 358a's plain-s1/plain-s2: its registered test counts are reused (same code path, seeds,
data stream); plain is not re-run.
Graded: flow right after n = 32 Euler steps (fixed in advance; fixed test noise).

| mark | what (each seed) | pass |
|---|---|---|
| G0 validity | flow and plain each ≥ 210/300 on the practised tests (sums4, grids5, numbers4) in at least 2 of 3 kinds | else INCONCLUSIVE |
| F1 | bigger tests, flow − plain: ≥ +30 on at least 2 of sums6 / grids6 / numbers5, and ≥ −10 on the third | yes |
| F2 | practised tests, flow − plain ≥ −10 on each | yes |
| report | flow at 16 and 64 steps; flow vs 358a's loop (own stop) per test; sums8, grids7; training curves | - |

**PASS = G0, F1 and F2 on both seeds.** G0 met on both seeds and anything else = FAIL (stays FAIL).
**Proved wrong** (for looped flows on these puzzles at this size): G0 met and flow − plain ≤ +5 on all three bigger
tests, on both seeds.

Kept from 358a on purpose: the +30 bar (the papers thread's draft said +20; keeping 358a's bar so the two runs compare
and no bar is lowered after a failure). No stop-picks-length mark: the flow always integrates to t = 1 (a known
conflict with 358a's G3 idea, stated in the handoff).
Prediction before running: grids6 likely stays well above plain (358a's loop did +67/+76); sums6 is the open question
(358a's plain scored 197 and 255); numbers5 ~0 for both (358a memorised numbers; unchanged here). PASS maybe 25%.
Limits: the flow does many rounds per question (same weights, not same compute); the paper's own baselines were copied
from other papers and it has no bigger-than-practised test; an unregistered CPU sanity preview on dev sums
(preview/, never the sealed tests) checked only that the code learns.

Sanity preview result (unregistered; read before sealing; changed nothing): small flow net, 4,000 CPU steps, dev sums
4/6/8 digits: 200/177/78 of 200 at 32 steps (16 steps: 200/182/85; 64: 197/168/73). Same settings as the 358a sums
preview (loop 200/175/88, plain 195/155/42). The code learns; n = 32 stays as fixed.
