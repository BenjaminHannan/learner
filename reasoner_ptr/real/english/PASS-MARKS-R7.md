# Question-first reuse and a thin talker: pass marks (fixed 2026-10-04 before any training run)

Ask: Ben 18:36 UTC 10-04, "why would the second language model read the question? Shouldn't it just output a sentence?" Decision card (18:37 UTC) recommended "Both"; work goes ahead on it while the card is open. Fast lane, 6 paired seeds, about $1 to $2.

## Three runs per seed (seeds 0 to 5), all on the same box
All three use `--gen 8000 --kinds 6 --block-r6`, 2000 updates of 16 rows, and the same lr. This is round 6's "six" recipe.

- **allptr (control, rerun):** today's talker. Its input is [8 pooled core vectors][8 pointer vectors][every question word][BOS][answer]. It reads the question a second time.
- **qfirst (reuse):** the input is [BOS + question words][8 pooled + 8 pointer vectors][answer]. The question comes first, as in the first read. At test, the second pass reuses the first read's LM cache and only processes the 16 core vectors plus the answer. Training uses the same sequence without the cache. A dry run checks that both give the same logits.
- **ptr (thin talker):** the input is [8 pooled + 8 pointer vectors][BOS][answer]. The talker sees no question words, only what the core hands it. This is the state-only talker, with the pointer as its copy path.

## Test sets (unchanged)
- FRESH-EN-R3.json (192 questions)
- NEW-KINDS-R5.json (sha256 eafb2a556ba8…, 192 questions)
- NEW-KINDS2-R6.json (sha256 a3b8ec7baddb…, 192 questions)

**Pooled exact** means exact accuracy over all 576 questions.

## Judged A, reuse keeps accuracy: qfirst − allptr, pooled exact, paired by seed (df 5, t = 2.571)
- **PASS:** the 95% t-interval's lower bound is above −5 points.
- **FALSIFIED:** a mean below −5.
- **In between:** anything else.

## Judged S, reuse is fast: qfirst batch-1 time to first answer token, divided by the bare LM's on the same box
- Each run times 48 FRESH questions at batch 1, with cached decoding for both paths, after all three runs on the box have finished eval. The runs are timed one at a time, and the first 5 questions are a warm-up.
- The ratio is a median over questions, then a median over the 6 boxes.
- **PASS:** a ratio of 1.5 or less.
- **FALSIFIED:** a ratio of 2.5 or more.
- **In between:** anything else.
- allptr's ratio (two full reads) is reported next to it as the reference.

## Judged B, the talker needs no question words: ptr − allptr, pooled exact, paired by seed
- **PASS:** the lower bound is above −5 points.
- **FALSIFIED:** a mean below −10.
- **In between:** anything else.

## Read, not judged
- Each test set separately.
- The bare 8-shot bar from rounds 5 and 6:
  - FRESH 75.0
  - NEW-KINDS-R5 67.7
  - NEW-KINDS2-R6 77.6
- Lesions:
  - zero_pool for all three arms;
  - zero_core (all 16 core vectors zeroed) for qfirst, which shows how much the question-first talker leans on the core.
- Time to 8 answer tokens.
- "contains" accuracy.
- Per-kind accuracy.
