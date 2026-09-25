# lis-319: the reader reads the conversation, not one turn (one change on top of lis-318)

Thread "Fix: reading facts from chat". Written 2026-09-25 03:00 UTC, before any lis-319 data was labelled, any training
ran or readpanel319 was sealed or run. Road map: design/v3/30-modes/370-reading-roadmap.md.

## Why
lis-317 (DEV): owners that point back to an earlier user turn ("she's 84", "his girlfriend Thea", "nan's pug") cannot be
read, because the reader sees only the assistant's last reply. Sleep's night re-read (Fix: sleep thread) will also call
the reader over a whole day of chat. lis-319 gives the reader up to 6 earlier user turns with the assistant's replies.

## The one change
The reader's input: scripts/claude_lis319_common.build_prompt_hist (earlier chat + last reply + turn). Everything that
serves it is part of the same change: every training row is re-prompted with its history ("(none)" for single-turn
sources); chat318 rows labelled UNCLEAR for a history-less reader are dropped (216 train copies, 3 dev); about 1,500 new
dialog rows written from scratch by 3 Opus agents to need history (brief data/WRITER319.md: backref, local,
short_answer, correct, ambiguous, ask, nosave, smalltalk) are added when a blind second labeller who also read each
dialog in order reproduces them (data/LABELLER319.md; scripts/claude_lis300_agree.py). Builder:
scripts/claude_lis319_data.py. Reader: scripts/claude_lis319_read.py (Reader319, same confidence code; read_dialog for
offline use). No LoCoMo or LongMemEval text, and nothing built from them.
Unchanged from lis-318: base model, LoRA settings, epochs 2, lr 2e-4, rank 32, batch 16, seed 300, frame format,
compiler, threshold rule. max-len 256 -> 512 (a history prompt is longer; rows over 256 tokens would be cut): the
only hyperparameter that moves, and only because the input is longer.

## Registered test
artifacts/claude-readpanel319-20260925 (TEST-ONLY; 30 dialogs x 8 turns, each fact tagged needs_history; written
blind by a separate Opus agent with a blind second labeller; sealed before any lis-319 training). Run ONCE per arm.
Arm A = lis-318 reader (turn + last reply only). Arm B = lis-319 reader with history (scripts/claude_lis319_rows.py
builds the history from the panel's own dialog order). Each arm at its own dev T. Scorer: scripts/claude_lis319_score.py.
If lis-318 is a registered FAIL, arm A is still the lis-318 reader (the thing lis-319 changes).

## Marks (fixed now)
| Mark | Bar |
|---|---|
| H1 back-references: B's R0 on needs_history facts | >= 70% of them AND >= A's + 40 points |
| H2 no loss elsewhere: B's R0 on the other facts | >= A's - 3 points |
| H3 safe: B's wrong_turns at its T | <= 2 of 240 |
| H4 no invention: B's nofact_rows_with_save | <= 1 |
| G1 single-turn dev (lis-301 dev + chat318_dev, all-or-nothing hits at each arm's T) | B >= A - 3% |
PASS = all five. Proved wrong: B's H1 <= A's + 10 points -> the reader does not use history from the prompt; the next
step is a different mechanism (an explicit reference-resolving step), not more rows.
