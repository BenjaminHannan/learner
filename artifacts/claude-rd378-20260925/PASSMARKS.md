# rd-378: memory notes beside the raw turns (the note writer's first test)

Thread "Fix: reading facts from chat". Written 2026-09-25 19:47 UTC, before any note-writer training and before
notepanel378 is sealed or run. Design: design/v3/30-modes/382-memory-store-interface.md (note-writer section) and the 370 road map
"Direction change" (Ben 19:22 UTC: relation facts are ~1% of the work).

## The one change
Add notes to the store. A: raw turns only ("heard"). B: raw turns + the notes the note writer (MiniCPM5-1B + its own LoRA,
scripts/claude_rd378_write.py) writes for every non-assistant turn of the panel dialogs, each citing its turns.
Same retriever for both (BM25 + the stack's frozen MiniLM, reciprocal-rank fused; scripts/claude_rd378_eval.py), same questions.
Note-writer training: scripts/claude_rd378_data.py over dialogs and notes written from scratch by Opus agents, kept only where a
judge found every note ok and nothing missed; LoRA settings as the reader (epochs 2, lr 2e-4, rank 32, batch 16, max-len 512,
seed 300). No DEV bank, panel, bank A/B, LoCoMo or LongMemEval text in any training row.

## Registered test
artifacts/claude-notepanel378-20260925 (TEST-ONLY; 30 dialogs, 15 chat + 15 overheard, 12-16 turns; 180 questions, 6 per
dialog: single, time, multi, latest, preference, none; evidence turns marked; written by a separate agent, answers checked
by a blind answerer; sealed before any rd-378 training). The writer runs over it ONCE. Evidence found@k = any evidence turn
among the turn ids of the top k items ("none" questions skipped).

## Marks (fixed now)
| Mark | Bar |
|---|---|
| N1 multi-turn questions: found@10 | B >= A + 10 points |
| N2 time questions: found@10 | B >= A + 5 points |
| N3 all questions: found@10 | B >= A + 5 points, and no type more than 3 points below A |
| N4 notes true to their turns: a blind judge (the training judge's brief) marks "unsupported" | <= 5% of B's notes |
| N5 notes parse | unparsed turns <= 2% |
PASS = all five. Proved wrong: all-question found@10 B <= A + 1 point (notes don't help finding).
Report only: allfound@k per type, found@5, notes per turn, write ms per turn, the judge's other verdicts.
