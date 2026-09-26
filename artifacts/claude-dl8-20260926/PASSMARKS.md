# dl-8: does a night that practises only what the model still finds hard keep learning and cut forgetting, beyond
# training on fewer rows? (Fix-sleep thread. Registered when this file is committed, before any run.)
Code: scripts/claude_dl8_gated.py (the docstring is the method). Reuses claude_dl1_nights unchanged and the GLM puzzle
instruction pinned by claude_dl6c_glmframe (frames.json sha256 3c1fe9c1...14bc). Replaces PLAN-draft.md's grid idea,
which waits on GLM grid wording (new GLM jobs are paused, Thread manager 18:48).

## Why
- dl-6 (registered FAIL) report-only dose split: at matched total training, 1 and 3 epochs lost about the same and
  learned about the same; forgetting tracks the amount trained. dl-5: grids learned in one night, then only forgetting.
- Brain first: sleep strengthens what is new or still weak (prediction error); consolidated memories are not
  re-trained. Silicon version: the current model scores each practice row before the night; only the harder half is
  practised. A random half of the same size is the dose control, so a pass cannot come from training less alone.

## ONE change from dl-2's night: which rows are trained
Arms on the same day and the same code-checked rows (the 1B's own right expressions, bare, no sentence frame):
S = every row (dl-2's night: 3 epochs, lr 2e-4, batch 8, one growing LoRA r16 on q,k,v,o);
E = the half with the highest current loss (answer-token loss under the model as it is before that night);
R = a random half (same count as E). Seeds 14 and 15, 7 nights, 150 puzzles a day, 30 guesses; TEST seed 3190 (100
fresh puzzles x 20 guesses at dl-1's temperature); HARM = the 300-item panel, lost = right at base, wrong now. The
puzzle instruction is GLM 5.3 Flash's (not Claude's) in every arm, TEST and base measure alike. Machine: BensPC.

## Marks (night 7; score() computes them)
- H1 forgetting cut: E's lost <= 0.5 x S's (sums over seeds), and each E seed is below each S seed.
- H2 still learns: E's lucky >= 2 x L0 on each seed, and E's gain over L0 >= 0.8 x S's gain (sums).
- H3 which rows matter, not only how many: E's gain >= R's gain + 0.1 x S's gain, and E's lost <= R's lost (sums).
Verdict: PASS = H1, H2, H3. INCONCLUSIVE if L0 < 10 or S's night-7 lost sum < 20. Proved wrong: E and R within 20%
of each other on both gain and lost (picking hard rows makes no difference beyond the count).

## Reported, not marked
Per night: rows trained, the median loss of all rows and the smallest kept loss (E), lost/gained vs base and vs the
night before, KL, greedy solves, reached. The dose split (lost and lucky against cumulative trained rows x epochs)
for all three arms.

## Limits stated before the run
Number puzzles only; the day is mostly unsolved greedily, so "hard" here means high loss on a checked answer, not
"never solved". Two seeds. The frame differs from dl-2..dl-7 (GLM wording), so absolute numbers are compared only
within this run.
