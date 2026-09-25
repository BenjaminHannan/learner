# rd-378 note-writer training data (2026-09-25)

Written from scratch by 6 Opus agents (brief WRITER_NOTES.md), 60 dialogs each (30 chat with an assistant, 30 overheard
two-person chats), 8-14 turns, notes per non-assistant turn. No LoCoMo or LongMemEval text and nothing built from them; no
panel, bank A/B or DEV-bank name used (script name check per writer). A separate Opus judge per file (JUDGE_NOTES.md)
gave every note a verdict and every turn a "missed" count: judge_w*.jsonl.
Verdicts ok / total: w1 530/556, w2 478/495, w3 482/500, w4 448/478, w5 533/542, w6 465/493 = 2,936/3,064.
Builder (scripts/claude_rd378_data.py) keeps a turn only when every note is ok and nothing was missed.
Dry run: { "dev_dialogs": 31, "dev_rows": 255, "dropped": 232, "kept_dev": 255, "kept_train": 2550, "notes_kept": 2797, "train_rows": 7650, "turns": 3037}
dev_dialogs.jsonl = the 31 dev dialogs without notes (for the writer CLI). Longest prompt+target 1,319 characters.
Relation-type notes are 2-8% of notes per file (Ben 19:22 UTC: relations ~1% of the work).
