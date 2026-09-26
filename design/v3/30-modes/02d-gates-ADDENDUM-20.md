# 0.2d gates, ADDENDUM-20: notes slot. Written 2026-09-26 16:53 UTC, before any run

The Thread manager ruled at 16:53 UTC that rd-378L cannot ship, because its writer was trained on Opus-written dialogs
and notes with Opus-judged labels, and Ben's 16:39 rule applies. Trustworthy notes will retrain the writer from the plain 1B on
GLM data. It must match rd-378L on real LoCoMo chats (that owner's marks, sealed before training).
This replaces ADDENDUM-12's "Notes: rd-378L when it passes".

- Notes slot = the retrained writer, if it has a verified PASS. 0.2d waits for that writer's registered verdict,
  PASS or FAIL. It does not wait indefinitely for a PASS.
- Fallback N0, fixed now: if the writer FAILs, 0.2d ships with no written notes. The notebook holds lis-320's frames
  plus a pointer to each raw user turn, and recall reads the pointed-to turns. The report discloses this.
  Ben's design says notes are pointers to the raw chat, so N0 still shows exact recall with provenance. The memory win
  row (rp1 arm J), S1/H3 and H1 are judged the same way either way, with no change to any bar.
- Nothing else changes. The headline gates stay H-A, H-B and H-R.
