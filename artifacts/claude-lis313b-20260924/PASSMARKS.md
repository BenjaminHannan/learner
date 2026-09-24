# lis-313b: re-run of lis-313 after a crash fix (marks unchanged)

Written by the listener thread (Opus) on 2026-09-24, before any lis-313b run.

lis-313-f0 was BLOCKED, not failed. Arm A finished, then arm B crashed after 13 of 40 dialogs with "MPS backend out of memory". Cause, reproduced on CPU:
- 292t's per-turn snapshot (claude_fix260_openers.snapshot260) walks the loop's helper objects and deep-copies their plain attributes.
- The reader object was reachable from the loop, so the 1B model's weights were copied on every turn until memory ran out.

The fix is in scripts/claude_lis_stackb.py: MemoReader keeps the reader inside a closure, which that walk does not follow.

Two changes from lis-313, nothing else:
1. **Crash fix:** scripts/claude_lis313b_f0.py wraps the reader in that MemoReader, for arms B, C and D.
2. **Arm D uses scripts/claude_lis313b_agent.py:** it answers only when the question word fits the looked-up relation. A where-question needs a place relation, a when-question a date relation, and a who-question a person relation. This was found on the month-end DEV bank (not F0). There, "where does my sister live?" misread as a question about the sister was answered "Your sister is Tuva.".

The marks are exactly those in artifacts/claude-lis313-20260924/PASSMARKS.md (P313.1 to P313.4), plus P312.1 to P312.4 scored from the same run. F0 was never read item by item by the listener thread.

CPU tests:
- scripts/claude_lis313_test.py 11/11.
- scripts/claude_lis314b_test.py 16/16. b1 (question-word check) and b3 (no deep copy of the reader's model) fail on the old code.
