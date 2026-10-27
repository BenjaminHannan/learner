# bm-395 PLAN: ep-382's answering test (benchmarks thread, 2026-09-25, written and sealed before any run)

Question: does the plain MiniCPM5-1B answer LoCoMo questions better when it is shown the 10 chat lines the
shared memory store recalls (store v2, scripts/claude_ep382_store_v2.py, fused MiniLM + BM25) than when it is
shown the 10 lines BM25 picks (bm-390's Rb arm, 25.06 F1 on categories 1-4)? This is the GPU test agreed with the
month-end thread for ep-382 (episodic memory of heard turns). Ben's 19:38 UTC note: no questions to him until
about 23:40 UTC, take initiative; month-end's episodic-memory card is taken as its recommended "yes".

Development measurement on LoCoMo practice: every number is labelled "after using LoCoMo for development"
(the store's row format was picked on LoCoMo in bm-393c). Nothing is trained. LongMemEval is not touched.

## Arms (one rented GPU, one run, each command once)
- E: scripts/claude_bm395_store_answer.py, k = 10. The ONE change against Rb is which turns are shown. The
  prompt layout, question text (with bm-390's category-2 hint and category-5 options), system prompt, greedy
  decoding, 50 new tokens and thinking off are bm-390's sealed code, called unchanged. The store query is the
  question exactly as the model is asked it, which is also Rb's BM25 query. Self-test: with every turn shown,
  the layout is byte-identical to bm-390's bm25_context (BM395-SELFTEST PASS on the smoke data and LoCoMo).
- Rb2: bm-390's own Rb command re-run on the same machine (scripts/claude_bm390.py locomo --arm bm25:BASE).
  It is the registered baseline, so machine differences cancel.
- E20 (report only, decides nothing): the same as E with the store's top 20.
- Rb (bm-390, BensPC, 25.06) is reported beside Rb2.

## Pass mark (fixed now)
Scored with scripts/claude_bm390_score.py unchanged (the LoCoMo repo's clean-up and F1; categories 1-4, 1,540
questions; paired bootstrap, seed 390, 10,000 resamples): `--primary E --baselines Rb2 --report Rb,E20`.
PASS if E - Rb2 is at least +3.0 points AND the 95% interval's lower end is above 0 (bm-390's M1 rule).
Anything else is a registered FAIL. If Rb2 differs from Rb by more than 1.0 point, that is reported and E - Rb is
reported too, but the verdict stays E against Rb2.
Validity: 1,986 rows in each of locomo_E, locomo_E20 and locomo_Rb2, every command exit 0, seals OK. An arm that
fails validity is NOT RUN; the verdict needs E and Rb2.

## Predictions (before the run)
- H1: E - Rb2 on categories 1-4 is between +1.0 and +7.0 points. Basis: in bm-393, Rb scored 38.3 F1 when BM25's
  top 10 held an evidence line and 10.9 when not; store v2 finds one for 65.9% of questions against BM25's 51.7%
  (bare question), which gives about +3.8.
- H2: the pass mark is met. I lean yes, about 55%: the expected gain sits just above +3.
- H3: E's gain over Rb2 is bigger on multi-hop (category 1) than on single-hop (category 4).
- H4: Rb2 is within 1.0 point of Rb's 25.06.
- H5 (report only): E20 scores above E on categories 1-4.
- H6 (category 5, outside the mark): E's category-5 F1 is within 5 points of Rb2's.

## What each result leads to
- PASS: the store's recall(top 10) is the episodic-memory answer path month-end joins into 0.2 (notebook facts
  first, the store when the notebook has no answer). A different k is a separate registered test.
- FAIL: the store stays (it finds more lines), but more retrieval tuning on LoCoMo stops; the next lever is the
  answering step (with the evidence in view the plain 1B's F1 is only about 38).

## After the run (not part of the verdict)
A report-only CPU count of how often the recalled top 10 held an evidence line with this query (the question as
asked, not bm-393c's bare question), and F1 split by found / not found, as in bm-393.
