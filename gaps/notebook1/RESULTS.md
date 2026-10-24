# Notebook-1 results (60 questions, 1 seed)

Stand-in models (untested for the local model): writer and reader `claude-haiku-5-5` (effort low), judge `claude-sonnet-5-5`. Arms and pass marks unchanged from PREREG.md. All labels below are **shown** for this sample only; any claim about other models or the real assistant is **untested**.

| Arm | Overall | KU | MS | SS-asst | SS-pref | SS-user | Temporal | Mean prompt tokens |
|---|---|---|---|---|---|---|---|---|
| F full history | 76.7% | 80 | 80 | 100 | 20 | 100 | 80 | 167,054 |
| R BM25 pairs | 71.7% | 90 | 50 | 90 | 30 | 90 | 80 | 7,999 |
| N notebook | 56.7% | 80 | 40 | 50 | 40 | 80 | 50 | 1,548 |
| O oracle | 86.7% | 100 | 90 | 100 | 60 | 90 | 80 | 8,277 |

Paired (questions where only one arm is right): N vs R: N wins 7, loses 16. N vs F: N wins 3, loses 15.

## Verdicts
- P1 (N >= R + 8 pts): **FAIL** (N 56.7 vs R 71.7, -15 pts). Shown.
- P2 (N >= R on knowledge-update + temporal-reasoning, 20 q): **FAIL** (13 vs 17). Shown.
- P3 (N prompt <= 1/20 of F and N >= F - 10): **FAIL**. Token ratio 0.9% passes, but N is 20 pts below F. Shown.
- "Wrong if N <= R overall": triggered. In this form (one-pass dated notes, BM25 top-20 lines, Haiku writer) the notebook did not beat plain search of raw chats. Shown for this sample; whether a better writer, more lines, or the local model changes this is untested.

Noise: SE about 6 pts per arm; the N-vs-R gap (-15) is about 2 SE of the difference on paired counts (7 vs 16), suggestive not conclusive.

## Suggested (not tested)
Notes lose specifics, since the writer compresses each session without knowing the future question (single-session-assistant 50% vs 90% for R). Retrieving only 20 note lines may also miss multi-session counting questions (MS 40%). Temporal drops may come from note line dates versus the reader's date arithmetic. None of these was isolated.

## Data surprises / problems
- Dataset has 500 items, fields as expected. `answer` is an int in 32 items (cast to string via f-strings). Sample drew 5 abstention (`_abs`) items.
- Haystack sessions are not guaranteed ordered in the file; I sorted by date string.
- F first pass hit Anthropic 429 token-rate limits (27 of 60 failed, recorded as wrong); I reran only the errored rows at low concurrency until 0 errors. Reported F numbers are after the rerun. First-pass F was 43% only because of those errors.
- No refusals recorded.
- Judge prompts are my approximation of LongMemEval's per-type grading, not the official script.
- Spend: see result.json; estimated total about $7.5.

## Notebook-1b (Addendum 1): hybrid arm H
Arm H = R's top-10 raw turn pairs plus N's top-20 notes (date-sorted, later notes replace earlier) in one prompt; same reader, judge, sample and cached notes. Shown for this sample (Haiku stand-ins, one seed).

| Arm | Overall | KU | MS | SS-asst | SS-pref | SS-user | Temporal | Mean prompt tokens |
|---|---|---|---|---|---|---|---|---|
| R | 71.7% | 90 | 50 | 90 | 30 | 90 | 80 | 7,999 |
| H | 73.3% | 90 | 50 | 90 | 40 | 80 | 90 | 9,430 |

Paired H vs R: H wins 5, loses 4.
Verdict (H >= R + 5 pts): **FAIL** (H 73.3 vs R 71.7, +1.7 pts). "Wrong if H <= R": not triggered. Differences this size are within noise (SE about 6 pts).
Extra spend about $0.1 (cap $3). H had no errors.
