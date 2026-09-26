# 0.2d gates, ADDENDUM-35: where the W input goes. Written 2026-09-26 21:55 UTC, before any seal or run

Making things up about you reported this at 21:55 UTC. Month-end checked it against artifacts/claude-mu405-20260926/VERIFY-V405b.md
(885df2bc3) and scripts/claude_y1f_layout.py:59-63.
- **Shown, as a registered validity count with a matching blind recount.** With the 'User said' block in the SYSTEM
  message, the plain 1B answered 4 of 60 direct asks about a stored fact. The comparisons are 0 of 60 with nothing given
  and 3 of 60 with 0.2c's fact lines. scripts/claude_e2e02d.py builds its W input in exactly that form (system_text).
- **Suggested, not shown.** Placement is the cause. y1f's L1 puts the block in the USER message, and bm-398d with that
  placement got 137 of 297 LoCoMo answers. That is a different panel and a different question form, so it is not a
  comparison.
- **Decision.** 0.2d's memory path as built probably does not reach the user. The build's W placement is not changed
  on a guess. It follows mu-405b, which makes one change on the same 60 DEV chats: the block moves from the system
  message to the latest user message. That run is free (CPU) and the other thread owns it. If mu-405b shows the move
  helps, system_text changes to that placement and nothing else changes. If it does not, the memory row is reported
  as it stands and the finding goes to the Thread manager.
No mark or bar changes.
