# MARKS-agent-aux-v2: "says it will act, then stops" in a long chat (track AGENT1, 2026-11-04 22:40)

Registered before any aux-v2 run.

**Why:** aux v1 did not reproduce the stop. Its control arm (no `stuck`) passed 9/10 in a short, fresh chat. The live failures happened at the end of Ben's long main thread.

**Tasks:** `aux_screen_long` and `aux_cancel_long` in tasks-aux.js. They are the same asks and scorers as aux v1, after 12 earlier everyday turns (~23k chars).
- Synthetic: the paragraphs repeat, which is less natural than Ben's real chat (not used: it is his data).

**Arms and runs:** control = src-v1 code, no kit. Test = `stuck`. 5 runs each, interleaved. Caps, lock and memory gates as before. Brain guard on (addendum 2).

**Pass mark:** `stuck` passes iff the test arm passes ≥ 8/10 task-runs AND passes ≥ control + 3. If the control passes ≥ 8/10, the stop is **not reproduced**: no verdict on `stuck` from this check.

**Also reported:** replies with a blank run and wall time per arm. Tasks overlapping app traffic (addendum 2) are flagged.
