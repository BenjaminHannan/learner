# Real-pipeline pointer test: pass marks (fixed 2026-10-03 ~22:38 UTC (commit 65d5bc859), before any training run)

Ask: coordinator relay 22:33 UTC (pointer vs no pointer on the real-model recipe, 6 paired seeds, fresh fast-lane
story set with new-word answers). Fast lane: generated held-out split; split seed, eval seed and marks written here first.

- Code: `run_story.py` on the real modules of PR #33 (commit 34608a1): contextual reader (HumanInputProjection on the
  frozen LM's last-layer states), real ordered 9.0M core (begin_latent + 4 advance_latent), real StatePrefix exit.
  No calculator calls (story task). 3000 updates x 16, lr 1e-3, AdamW wd 0.1, cosine, fresh weights. Seeds 0-5.
- Data: `gen_story2.py` (word split seed 20261004, eval seed 4242, fresh eval-only wording in every frame, stories
  capped at the core's 49 tokens). `EVAL-FORM-R2.json` sha256 3976d38c7d4b5a6c548540e5e31c7de18e82017b28b9dec14dbde8ded7322f30: 384 questions, 8 cells of 48.
  Unseen-answer stories use only held-out words, never in any training story.
- Arms: pool (today's real exit), ptr (pool + 8 pointer vectors), emb (pool + every question token's LM embedding,
  my reading of the PC session's fix). Paired by seed; 95% t-interval, df 5, t = 2.571.

## ptr vs pool, unseen-answer accuracy (192 questions) -- the judged comparison
- **PASS:** mean ptr - pool >= +25 points, interval lower bound > 0, ptr seen-answer mean >= pool seen mean - 5,
  and the uniform-pointer lesion loses >= half of the mean gain.
- **FALSIFIED:** mean ptr - pool < +8 points.
- In between: 4 more paired seeds, then the line stops.

## Read, not judged
- emb vs ptr on unseen and on all questions.
- Thin-talker check: with the 8 pooled (core) vectors zeroed at test, how much accuracy each of ptr and emb keeps.
  If emb keeps most of it, the LM is answering from the raw story and the core is bypassed.
- Train fit, per-cell accuracy, share of wrong unseen answers that are training words, pointer hit rate.
