# Real-pipeline recipe test: marks fixed before any training (2026-10-03, fast lane)

Question: do "copy path" + "varied training wording", which worked in the cloud reimplementation (PR #29), also work when the
model is built from the REAL pipeline modules (HumanInputProjection reader on frozen-LM lexical embeddings, real fresh 9.0M ordered
core, real StatePrefix 256-32-LM exit pooled to 8 vectors, real CalculatorPath heads and mechanical calculator, 4 loops, predicted
calls, real label policy)? Frozen LFM2.5-1.2B-Instruct, full FP32 (TF32 matmul), revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b.

Not the English pilot, not the PC checkpoints: all weights are fresh (checkpoints are not on the cloud). One departure from the
PC calculator run: batch 16 (equal-length buckets, the real core refuses ragged batches), 3000 updates, cosine lr 1e-3, AdamW
wd 0.1 betas (.9,.95) (the settings the reimplementation fit with), router auxiliary weight 0 as in the real calculator run.

## Held-out split (written before training)
- Answers 10..99 split once by seed 20261101 into 60 TRAIN answers (T) and 30 HELD-OUT answers (H). No training question has an answer in H.
- Eval form: built by `gen.eval_form()` with eval seed 20261103: 96 matched ADD/SUB pairs (192 questions), cells unseen/seen answers x
  train wording/new wording, 24 pairs each. Every eval operand pair is excluded from all training. New-wording frames are
  `templates_eval.json`; the composed training frames are pruned to share 0 sentences and 0 word 6-grams with them
  (`gen2.disjointness_report()`). Same generator family as the reimplementation, new split seeds, so not the earlier sealed forms.
- Training streams: 48,000 never-repeating questions per run; stream seeds 7,100,000+seed (old wording) and 8,100,000+seed (varied).
- Seeds 0-5, paired (same seed for both arms).

## Arms
- BASE: real exit as is (8 pooled prefix vectors), old 4-template training wording.
- RECIPE: BASE + the frozen LM's own embedding of the latest OK calculator result as a 9th prefix vector (zeros if no OK call), and
  half the training stream from the 180 composed frames.
- Exploratory, no marks (only if BASE and RECIPE both finish): COPY (copy path, old wording), WORD (pooled exit, varied wording).

## Measures (per run, on the eval form, the model's own calls, no gold at eval)
- final = first emitted token equals the answer AND the next token is EOS (teacher-forced on the correct token, like human_loss).
- right-call = in some loop the executed call is the task call (correct op, correct operand order for SUB).
- Cells: unseen/seen x train/new wording.

## Gate (validity)
BASE train fit (the 192 last training-stream questions, train wording) mean final >= 90% over the 6 seeds. If not, the comparison is
UNDERFIT-VOID: report it, draw no conclusion about the recipe.

## HEADLINES (paired over 6 seeds; t-interval t=2.571, n=6)
H1 unseen-answer final accuracy (96 questions): RECIPE mean >= 70% AND paired mean gain >= +40 points AND every seed gain >= +25.
H2 new-wording right-call rate (96 questions): paired mean gain >= +8 points AND 95% interval lower bound > 0 AND
   RECIPE train-wording right-call mean >= 98%.
PASS = gate met and H1 and H2 met. PARTIAL = gate met and exactly one of H1/H2 met. FALSIFIED = gate met and H1 paired mean gain < +15.
Anything else: no claim.
Also reported: seed SD per arm, final accuracy overall, wrong-unseen-answers that equal a training answer, right-call vs final gap.
Per-question rows for every run are copied back and counted before any box is destroyed.
