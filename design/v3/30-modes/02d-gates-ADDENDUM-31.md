# 0.2d gates, ADDENDUM-31: hand-written parts of the build, disclosed. Written 2026-09-26 19:06 UTC, before any seal or run

The coordinator's review (19:05 UTC) of scripts/claude_e2e02d.py found two hand-written parts its header did not name:
the date pattern DATE382 and the reasoner note added to the talker's input. Decisions:
- **Reasoner note (H1): kept, disclosed, cut to data.** It is the reasoner-to-talker hand-off. Without it the loop net
  cannot reach the reply, which would remove the reasoner from Ben's design. It now carries only the checked square, or
  "no square fits its clues", in one fixed frame, with no advice on how to reason. The learned part it stands in for
  (a talker trained to read the reasoner's output) is owed.
- **DATE382 (audit D15): kept, disclosed.** It only stamps store rows with the chat's date.
- The header now lists every hand-written part with what replaces it: P1 grid reader, P3 stop rule, C1 code check of
  the square, H1 hand-off, D15 date pattern, F1 newest value wins, N0 note text, W length switch.
- **Wording correction to ADDENDUM-29 item 1.** "CPU selftest 17 of 17" is a wiring check on stubs, with no model
  loaded and the slots empty. It says nothing about model quality, and it is reported that way from now on.
- The header's "I don't know" line now matches ADDENDUM-29: no doubt step unless y1t passes.
No mark, bar, panel or arm changes.
