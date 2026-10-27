# bm-398d PLAN: the evidence diagnostic (benchmarks thread, 2026-09-26 ~12:40 UTC)

Registered and sealed before any G or GD reply exists. A 3-question timing run (not scored, replies not read) and a
dry run of prep and score on fake labels were done first. Every LoCoMo number here is "after using LoCoMo for
development". LongMemEval stays untouched. Counts only: no question, answer or reply is quoted.

## Why
bm-397t (registered FAIL) raised LoCoMo F1 by shortening answers, but blind judges found no more right answers
(T 112, TS 107 of 300). An outside review (reviews/outside-review-bm397t-2026-09-26.md, every claim checked) asked
for one diagnostic before spending on retrieval or on training: when the plain 1B is wrong, is it because it
never saw the right lines (finding), because other lines mislead it (distraction), or because it misreads the
right lines (reading)? The plain 1B already gets the whole chat in T, so retrieval misses can't explain all of it.

## The one change
Only the chat lines shown to the plain MiniCPM5-1B change. Everything else is fixed: bm-390's header, the "DATE: /
CONVERSATION:" layout in time order (bm-395's store_context), bm-390's QA prompt with its category-2 date hint,
its system prompt, greedy decoding, 50 new tokens, thinking off (claude_bm390.generate).

| Arm | Lines shown | Source |
|---|---|---|
| G | only LoCoMo's annotated evidence lines | new, this run |
| GD | the evidence lines plus the store's highest-ranked other lines, to 20 lines | new, this run |
| E20 | the store's top 20 (bm-395's ranking, fused MiniLM + BM25) | existing, bm-395 run file |
| T | the whole chat | existing, bm-390 run2 |
| Q2 | the whole chat, read by Qwen3.5-2B (the rival bar) | existing, bm-390 run2 |

GD's extra lines come from E20's own ranking. So wherever E20's top 20 already held every evidence line (186 of
the 297), GD gets exactly E20's lines. GD − E20 then only comes from the other 111 questions, where retrieval
missed at least one evidence line (66 of them missed all).

## Sample
bm-397t's judged 300 (random.Random(3972).sample of the sorted category 1-4 question ids), keeping only questions
whose annotated evidence maps to chat lines: 297 kept (cat 1: 53, cat 2: 58, cat 3: 19, cat 4: 167). No kept
question has an unmapped evidence id. Evidence lines per question: 1 for 222, 2 for 41, 3 to 17 for 34.

## Inputs (sha256)
- LoCoMo locomo10.json 79fa87e9…8ff4
- E20: bm-395's locomo_E20.jsonl e7f70f57…bcef
- T: run2 locomo_T.jsonl 35bdf151…b3db
- Q2: run2 locomo_Q2.part1-5.jsonl b70f55be…555f, 3352ea2c…a129, 74c0eead…b448, 88ab38f9…b880, e6d702c9…b45c
  (full hashes in artifacts/claude-bm391-20260926/baselines.sha256.txt)
- Model: MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc (the same weights as T and E20)

## Where it runs and cost
This cloud machine's CPU (fp32), about 45 minutes, $0. T, E20 and Q2 ran on GPUs in bf16, so G and GD differ from
them in number precision too. Two checks measure that, both computed before any verdict is read:
- E20c: E20 re-run here for the first 30 questions; the count of replies identical to the GPU run.
- The 186 same-lines questions: GD and E20 got identical input there, so any difference is precision.
**Precision guard:** on those 186, GD's A-rate must be within 5 points of E20's. If not, D1 and D3 are reported
as suggested, not shown, and a GPU re-run of G and GD is proposed before anything is built on them.

## Blind check
- All five arms of the 297 questions: 1,485 main items, plus 120 relabel items.
- Five groups L0-L4 (Latin square): each group holds every question once, with the arm rotated, shuffled with
  random.Random(3981) into batches of 50.
- Twelve blind Opus judges, each in a private folder holding only its own batches and INSTRUCTIONS.md:
  - two per group, three batches each;
  - two relabel judges (X1: the first 60 questions as group L0 has them; X2: as L1 has them), neither of whom
    judges L0 or L1.
  - No judge sees two arms of one question. Judges see the question, the gold answer, the evidence lines with
    their dates, and one reply. They never see the arm.
- The rubric is INSTRUCTIONS.md: bm-397t's A-E labels plus the evidence lines. Because judges now see the
  evidence, T's A-count here is not comparable with bm-397t's 112; both are reported.
- The judge folders hold benchmark text and stay outside the repository.

## Decision rules (fixed now; coded in score())
All differences are A-rate points over the fully judged questions, with a conversation-level bootstrap 95%
interval (seed 398, 10,000 draws).
- **INVALID:** G − T ≤ −5. The annotated lines alone do worse than the whole chat, so LoCoMo's evidence
  annotations can't stand in for "complete evidence". No D1 verdict; move to the fresh bank below.
- **D1 (finding or reading), on G − T:**
  - "finding" if G − T ≥ +15 and the interval's low end > 0: giving the right lines fixes many answers.
  - "reading" if G − T ≤ +5: the 1B is wrong about as often even with only the right lines.
  - "both" otherwise.
- **D2 (distraction):** true if GD − G ≤ −10 and the interval's high end < 0.
- **D3 (retrieval misses cost answers):** true if GD − E20 ≥ +10 and the interval's low end > 0.

Report only: each arm's A-count and labels, by category; Q2 − T and Q2 − G (the rival's lead under a blind
check, which the outside review found missing); T − E20; GD − E20 split into same-lines and retrieval-missed
questions; relabel agreement; label agreement between judges on identical GD and E20 replies.

## What each outcome leads to
- finding: retrieval comes first (neighbouring lines, speaker and date kept, a second lookup for multi-part
  questions), checked by complete-evidence recall and the same blind check. Reader training waits.
- reading: the evidence-trained reader adapter comes first (398 follow-ups file, revised order).
- both: the reader adapter first, since every condition feeds it; a retrieval change registered alongside at $0.
- D2 true: reader practice includes misleading lines, and retrieval should hand over fewer lines.
- INVALID: go straight to the fresh bank.

## Predictions (fixed now)
| # | Prediction | Chance |
|---|---|---|
| P1 | D1 = finding; point guess G − T = +20 | 60% |
| P2 | D2 true | 25% |
| P3 | D3 true; point guess GD − E20 = +9 | 45% |
| P4 | not INVALID | 85% |
| P5 | Q2 − T ≥ +10 | 70% |
| P6 | G's A-rate ≥ Q2's | 50% |
| P7 | precision guard holds | 80% |

## Limits (stated now)
- LoCoMo's evidence annotations are incomplete in places, so G is "the annotated lines", not proven complete
  evidence. The INVALID rule catches the worst case only.
- This is one model on one dev set. Untested until later: a fresh, independently written bank with code-made
  evidence labels, to confirm whatever this finds. It comes second because LoCoMo already has evidence labels and
  three of the five answer sets, so this costs $0.
- Q2 is a different model; it is a reference, not part of the one change.

## Files
- scripts/claude_bm398d_evidence.py (selftest 6/6 PASS; run, prep, score).
- Runs: selftest; run on the sample; prep; the twelve judges; score with --out and --e20; a blind recount.
- The repository gets counts only: RESULTS.md, score.json, the key (ids and arms, no text) and the labels.
