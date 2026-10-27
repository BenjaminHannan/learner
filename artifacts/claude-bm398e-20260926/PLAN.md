# bm-398e PLAN: a copy-only span trimmer for answers that are too long (benchmarks thread, 2026-09-26 ~14:15 UTC)

Registered and sealed before any draft, span score or fit exists, and before the trimmer touches LoCoMo. Every
LoCoMo number is "after using LoCoMo for development". Counts only: no question, answer or reply is quoted.

## Why
Problem #4 is that answers from past chats are too long. bm-397t shortened them by training the model itself, and
math collapsed (GSM8K 191 → 42). The Mac agent's report (reviews/mac-agent-locomo-length-2026-09-26.md, claims
checked) showed a safer route: leave the model alone and trim afterwards with a step that can only copy the
model's own words. The perfect trim of T's own replies would score 48.3, and a fixed rule (delete the question's
words) reaches 32.39 over all ten chats. Asking the 1B to rewrite its answer failed in bm-397 and in the Mac
tests. The outside review (reviews/outside-review-bm397t-2026-09-26.md) warned that a vocabulary-only finaliser can
drop a negation or pick the wrong person's fact. Here the trimmer picks one contiguous span, so nothing is removed
from inside it, and a blind check guards meaning.

## The one change
T's LoCoMo replies (plain MiniCPM5-1B, whole chat, bm-390 run2, untouched) have their scored first line replaced by
one contiguous span of that same line (scripts/claude_bm398e_trim.py):
- The candidates are every span of 1 to 10 words within the line's first 40 words, with edge punctuation
  stripped, plus the whole line. Lines of 3 words or fewer are kept whole.
- The same plain 1B scores each candidate as the short answer, given only the question and the line: log P(span,
  then end-of-answer). The prompt is TRIM_USER in the script.
- The pick is the span maximising that score + LAMBDA × words + BETA × [whole line].
- LAMBDA and BETA are the only fitted numbers. They are grid-fitted to mean official F1 on the plain 1B's own
  drafts to code-made chats (scripts/claude_bm398e_data.py, seed 3980, 24 chats, 432 questions, sha256
  c19c82b3…b137). The fit uses the first 12 chats; the other 12 are a check.
- Nothing is trained, and nothing from LoCoMo is used to fit. GSM8K and MMLU never pass through the trimmer (it
  runs only on memory answers), so math and general answers are unchanged by construction.

The code-made chats use LoCoMo's layout and the bm-390 prompt, so the drafts are written as T's are. The question
kinds are wider than bm-397t's: single facts, why, how, opinions, dates in eight phrasings, and lists of 2 to 4.
Drafts are made on this CPU (fp32); T's LoCoMo replies came from a GPU (bf16).

## Steps (each once)
1. Drafts: `claude_bm398e_trim.py drafts` on the 432 code-made questions.
2. Spans: `spans --made` on those drafts.
3. Fit: `fit`, then write PARAMS.json.
4. Spans on T's LoCoMo replies (run2 locomo_T.jsonl, sha256 35bdf151…b3db), categories 1-4.
5. Apply PARAMS, giving TT.
6. Score with `score` (official F1, sealed bm-390 scorer).
7. Blind check with `claude_bm398e_judge.py`:
   - bm-398d's 297 questions, T vs TT, judges seeing the evidence;
   - 5 blind Opus judges: 4 main judges each take 3 batches of one group, 1 relabel judge;
   - private folders, and never two arms of one question to one judge.

## Marks (fixed now)
- **X1 (shorter and better scored):** TT's official F1, categories 1-4, all ten chats, ≥ 37.07 (TS, the trained
  short-answer model), with the conversation-level 95% interval of TT − T above 0 (seed 3984, 10,000 draws).
- **X2 (no right answers lost, blind):** TT's A-count ≥ T's A-count − 3 on the 297.
- **PASS** = X1 and X2.
- **Proved wrong:** TT's F1 ≤ 32.39, no better than the fixed question-word rule.
- Report only:
  - F1 by category and by half;
  - median words;
  - gained and lost questions, and replies whose overlap dropped to zero;
  - the fit and check numbers on code-made chats;
  - the T-by-TT label table;
  - relabel agreement.

## Predictions
- P1 (40%): X1 passes. Point guess: TT F1 36.
- P2 (70%): X2 passes.
- P3 (30%): PASS.
- P4 (85%): not proved wrong.
- P5 (70%): the check-half F1 on code-made chats rises over untrimmed by at least 10 points.

## What it leads to
- PASS: the trimmer is the fix for "answers too long" on the plain 1B. It goes to "Answering from memory" as one
  change inside the assistant, and to the next benchmark scorecard.
- X1 fails but X2 holds: a better picker is needed. The span scorer and the made-up chats are kept.
- X2 fails: trimming loses right answers, and the trimmer is not used.

## Files
- scripts/claude_bm398e_data.py (selftest 8/8), scripts/claude_bm398e_trim.py (selftest 8/8),
  scripts/claude_bm398e_judge.py (dry run on fake labels: prep 654 items, score ran).
- The repository gets counts only: RESULTS.md, PARAMS.json, the score output, and the judge key and labels.
