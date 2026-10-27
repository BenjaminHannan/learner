# bm-390 PASSMARKS (benchmarks thread, 2026-09-25; plan design/v3/30-modes/390-public-bench-plan.md)

Registered before any run on real benchmark items. Only made-up smoke items (smoke/, fictional people, written
by me) have been run. The code is sealed in SEAL-code.sha256.txt; the Premonition build is the one sealed for
336b (artifacts/claude-e2e336b-20260925/SEAL-code.sha256.txt must also check OK on the run machine).

## Data (downloaded at run time, sha256 checked against data-manifest.json)
- LoCoMo: snap-research/locomo @3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376 data/locomo10.json
  (sha256 79fa87e9...ff4): 10 conversations, 5,882 turns, 1,986 questions (cat 1: 282, 2: 321, 3: 96, 4: 841, 5: 446).
- MMLU-Redux-2.0 (edinburgh-dawg, rev 372ea425, CC BY 4.0), 57 subjects, 5,700 rows, 5,330 with error_type "ok";
  seeded sample of 300 (random.Random(390)); sample file sha256 is printed by `fetch` and must match the one
  recorded in RESULTS.
- GSM8K test (openai/gsm8k rev 740312ad, MIT), 1,319 rows; seeded sample of 300 (random.Random(390)).

## Arms (same text for every arm; greedy decoding; thinking off everywhere)
| Arm | What | Params | In marks |
|---|---|---|---|
| P | Premonition 0.1 = claude_e2e330c:build_330c, READER lis-301 + BASE MiniCPM5-1B @87179e5c, reads every turn, one sleep per session, each question from a fresh copy of the after-reading state | ~2.2B | primary |
| P_bare | P's same saved state, question without the repo's "write a short answer" wrapper | same | report only |
| T | plain MiniCPM5-1B @87179e5c, whole chat in one prompt (repo's chat-template baseline) | 1.08B | yes |
| Rb | T's model with the 10 best BM25 turns only | 1.08B | yes |
| C | T's model with no chat (contamination check) | 1.08B | report only |
| Q2 | Qwen3.5-2B @15852e8c (text model), whole chat; downloaded on BensPC in this job | 1.88B | yes, when it loads |
| L12 | LFM2.5-1.2B-Instruct @0f604ada, whole chat; downloaded on BensPC in this job | 1.17B | yes, when it loads |
General tests: P and T (and Q2, L12, report only) on MMLU-Redux-300 and GSM8K-300, a fresh P state per item.
A rival that will not load on BensPC (Windows, the job's venv) is reported as NOT RUN; nothing is rented or upgraded for it.

## Registered deviations from the LoCoMo repo's baseline code
Greedy decoding (repo: temperature 0.4 sampling); sessions in time order (repo's builder puts the newest session
first); speaker order from speaker_a/speaker_b (repo: an unordered set); category 5 uses adversarial_answer (the
data file has no answer field for 444 of 446 such items); category 5 option order fixed per question by seed 390.
The scorer's answer clean-up and F1 are the repo's (scripts/claude_bm390_score.py, VERBATIM block).

## Marks
- M1 (headline): LoCoMo categories 1-4 (1,540 questions), mean official F1. For EVERY arm X marked "yes" that ran:
  P - X >= 3.0 points AND the paired bootstrap 95% interval (10,000 resamples of questions, seed 390) is above 0.
- M3 (made-up answers): on categories 1-4, P's confident-wrong count (reply with no abstain phrase, official F1 = 0;
  phrase list fixed in the scorer) is lower than every "yes" arm's. Reported with M1; never a win on its own.
- M4 (no harm): P >= T - 3.0 points on MMLU-Redux-300 AND on GSM8K-300 (letter / final-number rules fixed in the scorer).
- Verdict: PASS only if M1 and M4 both pass. If a rival did not run, the verdict is partial and says so;
  a FAIL of M1 against any arm that ran is final for this build.
- Validity (else VOID, not FAIL): both seals OK; data sha256 OK; 1,986 LoCoMo rows for every arm and 300 rows per
  general arm; P's sleep log has one row per session (272) and checkpoint_exists true in every row; no traceback.

## Report-only numbers (fixed now)
Per-category F1 for every arm; category 5 official and strict (strict: right only if the reply picks the
no-information option by letter, or picks no letter and abstains in words); C's categories 1-4 F1 (above 10 points
= flag contamination or guessable items); P's stored triples after reading, check questions asked, sleeps with
learning attempted; P_bare vs P; published anchors (A-Mem Table 1, labelled "different harness").

## Predictions (made before the run)
- P390.1: M1 FAILS against T. P's categories 1-4 F1 is 3 to 15; T's is 15 to 35.
- P390.2: M3 PASSES against T and Rb (P makes fewer confident wrong answers).
- P390.3: M4 is a coin flip: P may route general questions to "I'm not sure" or to its calculator vote.
- P390.4: C's categories 1-4 F1 is at most 8 (little contamination).
- P390.5: Rb is within 5 points of T.
- P390.6: P_bare beats P by at least 2 points (the wrapper text confuses the reader).
What would count against the memory approach now: P below T on category 4 in both P and P_bare.
