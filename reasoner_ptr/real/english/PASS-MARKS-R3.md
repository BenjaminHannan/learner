# English rerun on the real pipeline: pass marks (fixed 2026-10-04 before any training run)

Ask: coordinator relay 02:01 UTC 10-04. Ben said "I don't care" when asked to pick between the pointer and all-words exits, so the default is all-words with the pointer kept. The next step is the English rerun on the real model with that setup. Fast lane: the held-out set and these marks are written first.

- **Code:** `run_english.py` runs on the real modules of PR #33 (commit 34608a1). It uses the contextual reader, the 9.0M ordered core (begin_latent + 4 advance_latent) and the StatePrefix exit, with no tool calls. Training is 2000 updates of 16 rows at lr 1e-3, with AdamW (weight decay 0.1) and a cosine schedule, from fresh weights. Seeds are 0 to 5.
- **Training:** the English pilot's bank `english_training_candidates_v3.json` (sha256 f2f5cce3…f9ac, the same bank as the PC pilot). It has 24 passages, each given as source_text and as paraphrase, with 2 questions per passage: 48 QA pairs and 96 rows. There are no auxiliary rows.
- **Fresh set:** `FRESH-EN-R3.json` (sha256 9e0ca5b5b069…), written for this round by a helper agent and checked by script. It has 48 new passages, 8 per family, with new names and mostly new answer words. Each question is asked of source_text (96 Qs) and of the paraphrase (96 Qs), 192 in all. It has nothing to do with the PC pilot's sealed fresh file or GOLD-PRIVATE.
- **Scoring:** greedy generation, then the bank's normalization (NFC, lower case, apostrophes, outer whitespace and final punctuation). A prediction must exactly match one of the listed accepted answers.
- **Arms:**
  - pool: today's exit.
  - allptr: pool, plus 8 pointer vectors, plus the LM input embedding of every prompt token.
- **Pairing:** by seed, with a 95% t-interval (df 5, t = 2.571).

## Judged: allptr - pool, fresh accuracy over all 192 questions
- **PASS:** the mean gain is at least +25 points and the interval's lower bound is above 0.
- **FALSIFIED:** the mean gain is below +8 points.
- **In between:** the result is reported as unsettled. No more seeds will be run on it.

## Read, not judged
- **Accuracy breakdown:** fresh accuracy for source_text and for paraphrase, accuracy per family, accuracy on new-word answers (short answers that share no content word with the bank), and train fit.
- **Wrong answers:** the share of wrong fresh answers that exactly match a training answer, which is the closed-set signature.
- **Core lesion:** allptr scored with the 8 pooled core vectors zeroed.
- **LM alone:** `lm_alone` is the frozen 1.2B instruct model with its chat template and no trained parts, run once. It is scored exactly and by "contains an accepted answer". It shows what the talker can do with no core at all.
