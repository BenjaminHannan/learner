# Our loop recipe vs the published tiny recursive models (TRM, HRM)

Sleep research thread. Written at the time in the commit, before any 358i result. $0, and it changes nothing about 358i.

Asked by the Thread manager after Ben (15:02 UTC): "why can't the one that thinks more do better? ... Maybe use recurrent networks?" Our loop net already is a recurrent network: one 2-layer block reused round after round. TRM (arXiv 2510.04871) and HRM are the published cases where a tiny recurrent net beats far bigger models on Sudoku, mazes and ARC. So the idea is sound. The question is which recipe choices differ.

## Sources and labels
- **Ours** is read from code: scripts/claude_rsn358a_run.py:41,116-127,291-301,363-365. 358g and 358i change the input and the attention only; the training loop is unchanged.
- **TRM numbers** are only those the repo already copied from the paper (design/v3/30-modes/358b-sudoku-extreme-plan.md:7-12, pages 3 and 11). Anything else about TRM or HRM is my recollection with no web check, and is labelled untested.
- **shown** means read in our code or the repo's paper notes. **suggested** means evidence points that way. **untested** means an idea only.

## Line by line

| # | Choice | Ours | TRM / HRM | Plausibly matters? |
|---|---|---|---|---|
| 1 | What the loss asks for | Each batch draws total rounds 1-16 and averages answer loss over the last k (1-6) of them. One batch in 16 has total=1, so the net is also graded on a round-1 answer (shown, :291-299). | Deep supervision over up to 16 steps. Each step starts from the previous step's answer and latent, carried forward detached, and is graded once at its end (shown in the repo notes: "up to 16 supervision steps per batch"). | **Yes, top candidate (suggested).** Ours rewards being right early, which is the 09-19 finding (maps_gaps_dropped.json:784: the same target at every loop removes the pressure for recursion). TRM avoids it because each graded step starts from the net's own partly-fixed state, so it learns "improve what's there". Nothing asks the first pass alone to be right. |
| 2 | How deep training recursion goes | At most 16 rounds × 2 layers per example. Gradient through the last 1-6 rounds; earlier rounds no-grad (shown, :116-127). | Per supervision step: T=3 cycles of n=6 latent updates + 1 answer update. Only the last cycle has gradient; the others are no-grad. Across 16 steps that is hundreds of block passes per example (shown: T=3, n=6, 16 steps). The "1-step gradient" ablation falls to 56.5 from 87.4 (shown). | **Yes (suggested).** At test we run 48 rounds but only ever train on ≤16, so rounds 17-48 are unpractised. TRM trains on its own long rollouts. |
| 3 | State | One state h. The answer is read from h (shown, :99-108). | Two states: answer y and latent z. z is updated n times from (x, y, z), then y from (y, z) (shown in repo notes). T=2, n=2 drops to 73.7 (shown). | **Likely (suggested).** A scratch state that is not the answer lets the net think without committing. Second candidate. |
| 4 | Weight averaging | None (shown, the AdamW loop at :270-305). | EMA 0.999. No EMA drops to 79.9 from 87.4 (shown). | **Yes, cheap (suggested).** Recurrent nets are unstable when trained deep. It could ride along with #1 as part of "TRM schedule". |
| 5 | Optimiser | lr 3e-4, weight decay 0.1, batch 256, 60k steps, cosine (shown, :363-365). | lr 1e-4, weight decay 1.0, batch 768, 2K warm-up, stable-max loss (shown). | **Maybe (untested).** Heavy decay fights memorising. Secondary. |
| 6 | Data regime | An endless fresh stream. Latin squares from a 20,000 pool per size. In the small maze trial plain fit the practised sizes fully (shown: loss 0.0001, 200/200 on 7x7). | 1,000 puzzles with heavy rule-keeping augmentation, very long training (60K epochs on Sudoku) (shown). | **Changes what "win" means (suggested).** TRM's win is largely generalising from little data, where a deeper plain net overfits. With endless data plain has no overfitting to lose to, and our win has to come from #9 instead. |
| 7 | Training compute | Loop and plain get equal steps. In every small trial the loop learns more slowly: maze trial loss 0.46 vs 0.0001 at 2,000 steps; 358i trial table (shown, artifacts/claude-rsn358m-20260926/trial, artifacts/claude-rsn358i-20260926/trial). | "Generally less than 36 hours" on one L40S for Sudoku (shown). | **Yes, as a confound (suggested).** At equal steps we may be comparing a finished plain net with a half-trained loop. |
| 8 | Stop rule | Halt head trained by BCE on "exactly right now" but never used in training. v2 rule at test (shown). | The Q-head is used in training to stop easy examples early (ACT), so compute goes to hard ones (untested recollection). | **Some (suggested).** Same exposure-bias pattern as the 09-19 finding (maps_gaps_dropped.json, HALT row). |
| 9 | What is tested | Size extrapolation: practise small, test bigger (shown, TESTS at :44-48). | Same size as training (Sudoku 9×9, Maze-Hard 30×30, ARC) (untested recollection). | **Important caveat (suggested).** The published wins don't cover our G1 claim. Loop-beats-plain at the practised size under TRM's regime would be the directly supported claim. |
| 10 | Size of net | 2×512 loop vs 8×256 plain, ~6.3M each (shown). | 2 layers, hidden 512, 5-7M. The paper's "less is more": 2 layers beat 4 (untested recollection). I don't recall a same-size, same-recipe plain twin in their tables, so check before relying on that. | **Matches already.** Not a difference. |

## Ranking for the post-STOP list (EXIT-RULE-ADDENDUM-1)
These go first, one change at a time, each with its own sealed pass marks:
1. **TRM training schedule** (#1 + #2, EMA #4 riding along): deep supervision over carried, detached state, no-grad cycles then one graded cycle, no loss on a bare first pass. Same net, same data, and the plain twin gets its matched best recipe. Prediction ~35% that it flips sums6/grids6 to a loop lead ≥+30 (untested).
2. **Two-state recursion** (#3): split h into an answer y and a latent z.
3. Then 358f looped flows (sealed e000c628e, held) and learned halting (#8).

Separate from the list, a check on #7 that the matched-compute rule allows: run both arms for longer, equally. If the loop's gap closes with steps, the losses so far were under-training, not the idea.

## Plain summary for Ben
Our loop net is already a recurrent network. The published tiny ones train it differently. They grade it only after it has had a go at fixing its own previous answer, and they train it on very long chains of thinking. We grade it after as little as one round of thinking, which teaches it to rush. They also give it a private scratchpad separate from its answer, and they average its weights to keep it steady. Their wins were on puzzles the same size as practice, from very little data. We test on bigger puzzles, from lots of data. If the loop keeps losing, copying their training method is the first thing to try.
