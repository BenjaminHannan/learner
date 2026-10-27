# Handoff: Looped Flows test to Sleep research (sent 2026-09-26 02:36 UTC)

The papers thread sent this to the Sleep research session, as the coordinator routed it under Ben's 02:17 UTC overnight go-ahead. The test is to be registered and run AFTER the 11:00 UTC deadline. Sleep research owns the design, the pass marks and the ID. The brief below is as sent.

---

PAPER: "Thinking with Looped Flows", arXiv 2609.11801. The full text is in the project files at research-2026-09-26/papers/2609.11801.txt. Check every claim against the text before registering.

WHAT IT IS: TRM's tiny shared core (2 layers, width 512, SwiGLU 1536; an MLP-Mixer of about 5M on Sudoku, attention of about 7M elsewhere), trained as a flow.
- Inputs: the net also sees I_t = (1-t)*x0 + t*x1 (x1 is the one-hot answer; x0 is Gaussian noise with sigma = 1/sqrt(|V|) on Sudoku), plus a time embedding. The extra input projection and time MLP (1->512->512) add about 0.27M weights (Sudoku: 5.03M -> 5.30M).
- Training: k = 16 steps with sorted t ~ U[0,1], so the noise falls at every step. The same x0, puzzle and answer are shared across all steps. Cross-entropy to x1 is taken at EVERY step, with the gradient stopped between steps. Each step runs 3 cycles, and only the last cycle gets gradient.
- Stop head: loss weight 0.5. It ends training rollouts early. At test time it is NOT used to stop; it only ranks 5 runs when ensembling.
- Inference: Euler (gamma = 0) or an SDE sampler from t = 0 to 1 over n steps (n = 128 on Sudoku).
- Sudoku only: an anti-overfitting "pseudotarget" trick (App. D) and weight decay 2.0.

NUMBERS (Table 1, 3 seeds, one run per puzzle): Sudoku-Extreme (1,000 practice puzzles) 97.9 +/- 0.4, against TRM 87.4 and FPRM 7M 94.2. Maze-Hard 86.7 +/- 1.1, no gain over FPRM's 87.0. ARC-AGI-1 58.8 +/- 1.8, against TRM 44.6. Fig 3: Sudoku accuracy goes from 74.5% at 8 steps to 97.9% at 128. Sec 5.1: TRM fails on 12.6% of puzzles, and 88.3% of those failures never settle on an answer; looped flows fixes 90.9% of TRM's failures.

CAVEATS: The baselines are copied from other papers, not rerun. Test-time compute is not matched: at 8 steps the flow model scores 74.5, below TRM. The ablations are single ARC runs. The pseudotarget trick is not ablated. There is NO test on puzzles bigger than the practised ones. The flow always runs to t = 1, which conflicts with 358a's goal that the stop head picks the length.

WHY IT FITS 358a (SUGGESTED): scripts/claude_rsn358a_run.py sets TRAIN_ROUNDS, GRAD_ROUNDS, TEST_ROUNDS = 16, 6, 48 and draws the total and graded round counts at random (lines 41, 291-292). Every graded round has the same target, so early rounds have no reason to build state that later rounds use. The flow instead spends extra compute as a finer grid over the same trained 0->1 range. Related: 2609.19107 App. B.4 finds tied loops get worse beyond the pass count they trained with, and random-count training only flattens this.

PROPOSED TEST (a draft; Sleep research owns it):
- Change: one package. Swap the 358a loop's training objective for the looped-flow objective, and keep everything else identical to 358a. Trim the width so the loop has the same number of weights as the plain twin, within 2%.
- Panel: freshly sealed, 300 items per test, at the practised sizes and the bigger sizes (sums6, grids6, numbers5).
- PASS: on both seeds, flow minus plain is at least +20/300 on at least 2 of the 3 bigger tests, and flow loses at most 10/300 on each practised-size test.
- REPORT ONLY: 16 steps vs 64 steps, and flow vs the 358a loop running on its own stop.
- PROVED WRONG: on both seeds, flow minus plain is at most +5/300 on all three bigger tests.
- Cost: about 2-3x the loop's training compute; fits in BensPC's 16 GB. Tell the Director before launching.

INFO ONLY: the 358b / bm-394 report-only line should cite the new same-size published scores (FPRM 94.2, looped flows 97.9). Idea B, the learned stop against a matched random stop, may overlap 358c1.
