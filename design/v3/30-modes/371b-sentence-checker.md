# 371b: a "does the source say this sentence?" checker (plan, not registered)

Thread "Fix: reading facts from chat", 2026-09-26 ~01:45 UTC. This is rd-371's one diagnosis-driven follow-up.

## Why
- rd-371 (VERIFY.md, main 3ee53ee7d): the relation-fact checker saved 15 vs 106. Causes: a lopsided bar rule (fell back to
  0.9999 instead of 0.995) and training prompts of at most 450 characters while the test was mostly long messages.
- rd-378 (VERIFY.md, main 10f87a9b1): the 1B note writer's notes are unsupported 113/360 on the sealed panel and 96/277 on
  dev (blind judge). Notes can't be stored or used without a check against their cited turns.
- Ben 19:22 09-25: relation facts are ~1% of the work, so the checker must judge plain sentences, not only triples.

## Design (one change vs rd-371: what the checker is trained on)
- Input: the cited source text (up to 6 earlier turns + the turn, same window the writer saw) + one sentence.
  Output yes/no, P(yes) as in rd-371.
- Training rows ("graded own drafts", no Claude-written targets):
  1. the 1B note writer's OWN notes on fresh dialogs, several samples per turn at temperature 0.7, each graded by the blind
     judge brief (data/JUDGE_NOTES.md); yes = ok, no = unsupported / wrong person / wrong detail.
     Seed set: artifacts/claude-rd378-20260925/dev_notes_judged.jsonl (277 notes: ok 167, unsupported 96).
  2. the reader's agreed relation facts rendered as plain sentences by code, with rd-371's code perturbations as negatives,
     now placed inside long multi-fact windows.
  3. hedges, plans, corrections, "our/we" and second-hand turns written as flat claims (code-made negatives).
- Bar rule, fixed before any run and the same for every arm: the lowest bar whose dev wrong-accept rate is no higher than the
  arm it replaces (for notes: at most 2% of accepted notes unsupported on dev).
- Dev and test must include long overheard and multi-fact chat (rd-371's dev had none over ~200 characters).

## Registered test (to be sealed before training)
Fresh blind dialogs; the note writer writes over them once; two blind judges grade every note; a note enters the key only
where both judges agree. Proposed marks: C1 accepted notes unsupported <= 3%; C2 keeps >= 80% of ok notes; C3 per-kind
(chat vs overheard) keep-rate gap <= 10 points. Proved wrong: at C1's bar it keeps < 50% of ok notes.

## Cost
Sampling the writer on ~200 fresh dialogs x 4 samples: ~1 h on BensPC ($0). Judge grading: blind Opus agents.
Checker training: as rd-371 (~6 min on a 5090) with max-len raised for 6-turn windows.
