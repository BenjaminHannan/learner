# rd-371b: a sentence checker trained on the note writer's own judged drafts (rd-371's one follow-up)

Thread "Fix: reading facts from chat". Written 2026-09-26 02:10 UTC, before the test dialogs are sealed, before the note
writer writes over them, and before any checker training. Plan: design/v3/30-modes/371b-sentence-checker.md.
Goal (Ben /goal 01:45 UTC): untrue 1B notes (rd-378: 113/360 unsupported on its panel, 96/277 on dev).

## The one change (vs rd-371)
What the checker learns from and reads. Source = the note writer's own window (up to 6 earlier turns + the latest turn),
question = one note sentence (scripts/claude_rd371b_common.build_sprompt). Training rows (scripts/claude_rd371b_data.py):
the rd-378 note writer's own notes (greedy + one sample at temperature 0.8, scripts/claude_rd371b_sample.py) on ~120 fresh
dialogs written blind for this purpose, each note graded by a blind judge (artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md):
ok/bad_cite -> yes, unsupported/bad_when -> no, bad_form skipped; plus code-made name/number swaps of ok notes -> no (no more
than the real "no" rows). No Claude-written sentence is a target; no panel, DEV bank, bank A/B/C/D, LoCoMo or LongMemEval text.
Checker: MiniCPM5-1B + LoRA, same settings as rd-371 except max-len 512 (epochs 2, lr 2e-4, rank 32, batch 16, seed 300).
Bar rule (fixed now, one rule for any arm): the LOWEST grid value whose accepted notes are at most 4% "unsupported" on dev =
the rd-378 dev notes (277, judged; artifacts/claude-rd378-20260925/dev_notes_judged.jsonl); if none, the largest grid value
(scripts/claude_rd371b_eval.py sweep).

## Registered test
artifacts/claude-notepanel371b-20260926 (TEST-ONLY; 30 fresh dialogs, chat + overheard, written blind by a separate agent).
The rd-378 note writer (sha256 dbcc8db5...8510) writes greedy notes over it ONCE. Two blind judges grade every note with the
judge brief; key = ok where both say ok, unsupported where both say unsupported, all else excluded (counted, reported).
Both judge files and the key are sealed before the checker is trained. The checker scores the notes ONCE at its dev bar.

## Marks
| Mark | Bar |
|---|---|
| C1 untrue notes stored: unsupported share of accepted (key ok + unsupported) | <= 5% (rd-378's N4 bar) |
| C2 good notes kept: key-ok notes accepted | >= 80% |
| C3 no kind left behind: chat vs overheard C2 | gap <= 10 points |
PASS = all three. Proved wrong: at its dev bar the checker keeps < 50% of key-ok notes.
Report only: no-checker baseline (accept all), excluded notes, median ms per note.
