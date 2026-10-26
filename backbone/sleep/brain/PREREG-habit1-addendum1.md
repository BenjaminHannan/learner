# Habit-1 addendum 1: drop "mentions" replies, retest on Week-1 (written 2026-10-26 ~17:55Z, before any Week-1 reply)

Labels: shown / suggested / untested. Stage 1 only (no training).

## Why
Week-2 stage 1 (RESULTS-habit1.md) failed only on false habits. All 23 false yeses on fact pairs read "Sam usually mentions X and Y together",
and no routine yes used that wording.

## One change
`habit.parse_habit` returns None when the reply matches `\b(mention\w*|talks? about|talked about|brings? up|refers? to)\b`. The prompt,
the model, the server and the settings are unchanged. The night code uses the same parser, so the change also applies to `--habit spot/ctrl`.

## Test (fresh data: Week-1, sha256 in data/week1.json.sha256; 12 routines, 40 fact pairs on 2+ days; habit1_probe_week1.jsonl, 64 questions)
- **S1a pass:** Rall valid yes >= 10 of 12 AND false yes on F <= 30% (12 of 40), both with the new parser.
- **Wrong if:** F false yes > 30% with the new parser (the model finds other wordings for "talk"), or Rall < 8 (the rule throws away real habits).
- Reported: R2; the Week-2 numbers re-scored with the new parser (post-hoc, not a mark).
