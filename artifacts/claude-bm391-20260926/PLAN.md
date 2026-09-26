# bm-391 PLAN: Premonition 0.2 candidates on the public benchmarks (benchmarks thread, 2026-09-26 ~01:30 UTC)

Registered before any run of these builds on any public test. Every LoCoMo number here is "after using LoCoMo for
development" (k = 20 for the memory store was chosen on LoCoMo practice, bm-395). LongMemEval stays untouched.

## What is tested
The three builds month-end sealed on main at da7e0f3a4. The seal is artifacts/claude-e2e382-20260925/SEAL-code.sha256.txt,
239 files; the seal file's own sha256 is 9bda3add859c310acc705dacbffdf8251ebe8687fc064379bc8e3cd85530e063.
- E = claude_e2e382:build_382b: 0.1 with the grammar fix (G), plus the memory store. When the agent would abstain
  on a question, it answers from the store's top 20 heard lines.
- R = claude_e2e383:build_383: G plus route383. When the agent would abstain on a question that is not about the
  user or anyone heard earlier, the plain 1B answers it.
- ER = claude_e2e383:build_383e: G plus the store (top 20) plus route383.

Harness and scorer: bm-390's, unchanged. Sealed files are scripts/claude_bm390.py and scripts/claude_bm390_score.py
(artifacts/claude-bm390-20260925/SEAL-code.sha256.txt, 8 files). Same data, same fetch hashes, same prompts, same
agent path as bm-390's P arm (one sleep per session, state restored before each question).

Baselines: fixed, not re-run. They are bm-390's registered run files listed in baselines.sha256.txt (paths on
origin/builder-outbox):
- T: plain MiniCPM5-1B, whole chat;
- Rb: plain 1B plus BM25 top 10;
- Q2: Qwen3.5-2B, whole chat;
- L12: LFM2.5-1.2B, whole chat;
- C: no-chat contamination check;
- P: Premonition 0.1.

## Which build the marks judge (fixed now)
0.2 is named by month-end's own registered marks on bank C: 382b's (PASSMARKS-382b.md) and 383's (PASSMARKS-383.md).
Those marks do not use any bm-391 number. The rule:
- both pass: ER;
- only 382b passes: E;
- only 383 passes: R;
- neither passes: no build is 0.2, and every bm-391 number is report only.
The other builds are reported in full, beside the named one.

## Marks (bm-390's, unchanged; X = the named build)
- M1: on LoCoMo categories 1-4 F1, X − B ≥ +3.0 with the paired bootstrap's 95% interval above 0. B is each of T,
  Rb, Q2 and L12 (seed 390, 10k resamples, the sealed scorer).
- M3: X gives fewer confident wrong answers (answered, F1 = 0, categories 1-4) than each of T, Rb, Q2 and L12.
- M4: X ≥ T − 3 points on MMLU-Redux-300 and on GSM8K-300, with the sealed answer pickers. That means at least
  13.67% (41/300) on MMLU and at least 60.67% (182/300) on GSM8K.
- PASS = M1, M3 and M4 all pass. Anything else is a registered FAIL. The contamination flag (C above 10) is already
  known clear (C 3.27).

## Report only
- Every arm's category split.
- Paired differences: E − P, ER − E and R − P on LoCoMo, and R − E and ER − E on GSM8K and MMLU.
- The store and route counters from EP382_LOG.
- The answer-length check scripts/claude_bm391_prf.py (median scored words, token precision and recall, replies
  ≥ 3x gold length; its F1 column must equal the scorer's).

## Predictions (fixed now; X is expected to be ER)
- B1 (98%): M1 fails against Q2 (X's F1 below 50.87). The registered verdict is FAIL.
- B2 (75%): X's LoCoMo F1 is between 6 and 25 (my point guess 14). The reasoning: 0.1's 617 non-abstained answers
  stay as they were. The store only helps the ~923 questions 0.1 abstained on. The plain 1B shown the same 20 lines
  scored 29.85 overall, but the agent's guards and its "say you don't know" prompt will reject or abstain on some.
- B3 (85%): E − P ≥ +5 F1 on LoCoMo.
- B4 (80%): |ER − E| ≤ 2 F1 on LoCoMo. route383 now keeps 1,361 of the 1,540 questions (they name a speaker heard
  earlier); only the other 179 can route.
- B5 (80%): M3 fails. X answers more than 0.1 did, and Q2 has only 402 confident wrong.
- B6 (85%): E's GSM8K is at most 60/300 (no route; the store is empty for a fresh general item).
- B7 (65%): R's GSM8K is between 140 and 200 (point guess 172). M4 on GSM8K passes for R with 35%.
- B8 (90%): R and ER each score at least 41/300 on MMLU (the M4 bar); point guess 145.
- B9 (70%): R − E on GSM8K ≥ +80.

## What would prove the idea behind 0.2 wrong (on these tests)
- E − P ≤ +2 on LoCoMo: the store fallback does not reach LoCoMo answers inside the agent, whatever it did for the
  plain 1B (bm-395).
- R − E ≤ +20 on GSM8K: routing abstained questions to the plain 1B does not recover math inside the agent.

## Where it runs
Rental (handoff/held/rent-bm391.md until the Director clears the money): one RTX 5090, three lanes in parallel.
- Lane 1: ER.
- Lane 2: E.
- Lane 3: R, general tests first.
Each arm is launched once. A crash with no output may be relaunched once with the same command, and that is
disclosed. Scoring and the recount happen afterwards on CPU, by this thread and a blind agent.
