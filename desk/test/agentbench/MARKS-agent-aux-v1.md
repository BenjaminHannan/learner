# MARKS-agent-aux-v1: "says it will act, then stops" (track AGENT1, 2026-11-04)

Registered before the first aux run. Separate from MARKS-agent-v1.md; the registered 20 tasks are unchanged.

**Why:** the lead's live UX test on the M1 (build 166fed5b4, 20:44–21:02) twice saved a reply that said what Glim would do, followed by a long run of blank characters and no tool call (3 and 4 minutes). The same pattern appears in 2 of 417 steps of the main bench baseline.

**Tasks (`tasks-aux.js`, run with `run.js --set aux`):**
- `aux_screen`: "what am I looking at on my screen right now?" A fake `screen_look` returns a window list. Pass = `screen_look` called and the answer names what is on screen (titration / Khan).
- `aux_cancel`: one preseeded turn creating the reminder, then "cancel that gym clothes reminder please". Fake `agent_list` / `agent_update`. Pass = `agent_update` on the gym Mote with stop or paused true, and the other Mote untouched.

Same settings, caps (240 s / 25 steps), lock and memory gates as the main bench. 5 runs per arm (2 tasks each, ~10 min per arm).

**Arms:** control = the version under test without `stuck`; test = the same plus `stuck`.

**Pass mark:** `stuck` passes the aux check iff the test arm passes ≥ 8 of 10 task-runs AND at least 3 more than the control. Also reported: replies with a blank run (`blank`), time.

**What proves it wrong:** test arm < 8/10, or gain < 3. `stuck` is then not offered for these prompts. Its main-bench result is judged separately by MARKS-agent-v1.md.
