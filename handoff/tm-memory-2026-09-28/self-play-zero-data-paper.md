---
name: self-play-zero-data-paper
description: Ben's 09-26 X post = "Self-Play Pretraining with Zero Data" (arXiv 2609.30063); verdict and the one sleep test it suggests
metadata:
  type: reference
  modified: 2026-09-26T02:07:25.461Z
---
Reviewed 02:1x UTC 09-26 in thread cmsg_01FuvegZXjMmeUzStiEFVnEWAG1BoJsGSmFpzdncTbC2r5 (tweet by Michael Y. Li, Stanford/TAU).
- Paper: generator writes Brainf*ck-like programs, learner (<25M params, byte-level) predicts their output; generator's RL reward = |<grad L(item), AdamW-precond * (theta_past - theta_now)>| with lookback e/2 ("learning progress"). Fetched via arxiv PDF + pypdf venv (fxtwitter API reads X posts; no WebFetch).
- Shown: adaptive generator >> fixed random-program prior (Fig 2); shuffled/negated reward worse (Table 5, 1M params, 4 seeds); ICL (reverse, stack, recall) emerges. Weak: zero-shot web text still ~4-5 bits/byte (Table 5: 5.34 at 1M); <25M only; hyperparams tuned on DCLM+DNA val loss; "hardness reward is gamed by noise" is argued, not ablated; signed reward beat canonical on text/C.
- Bearing on Premonition: none on saving/notes/refusals/length (facts can't come from self-play, paper says so). Relevant to sleep "dream just-too-hard puzzles" and a caution on "surprises first". Small-reasoner night picks day items uniformly (scripts/claude_slp358n2_nights.py night_batches).
- Ben said YES 02:06 UTC 09-26 (cmsg_01FuvegZXjMmeUzStiEFVnEWDf1rDvisTNtwh5CMGq5zBr); coordinator handed it to Sleep research, runs AFTER 11:00 UTC (overnight goal first). Test: slp-358n2 night + one change = day half of each batch picked by that score (L) vs uniform (U, = 358n2's S) vs shuffled-score placebo (Q), plus N. Marks told to Ben: L-U >= +20/200 on transfer_sums8 and transfer_grids6, both seeds; harm L >= N-6; Q doesn't match L. Proved wrong: L-U <= +5 on both, both seeds. Use fresh seeds (358t used 5, 6).
- Build hints (mine, not registered): sample items in proportion to score, not top-k (Creative found breadth matters); keep 358n2's 50/50 kind split; lookback theta_past = weights at half the steps so far (save a pre-training checkpoint); P from the pre-training AdamW second moment (night optimizer starts empty); <grad, v> per item via torch.func.jvp. Optional report-only arm: pick by loss (tests "surprises first"). See [[fix-sleep-line]], [[creative-line-333e]].
