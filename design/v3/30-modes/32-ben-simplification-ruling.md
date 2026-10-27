# Ben's simplification of the modes (21 Sep 2026) — owner ruling, overrides 31 where they differ

Ben's words (message cut off at the end): "It thinks, and there are no problems with thinking. If it gets too
full a memory it sleeps. Also, I should be able to have it work when I need, so it can take naps, but basically
work at my need. If it is working, then it can brainstorm for a bit using creative mode, then go back to work
once creative mode gets an idea. If creative mode decides it can't think of anything, it can ask me. Bored mode
can have access to the internet to look up stuff it thinks would be helpful to le[arn]".

## The simplified picture
- DEFAULT = THINKING (the old BORED). Thinking itself is unrestricted. What is restricted is only what gets
  WRITTEN: thoughts are `proposed`/`inferred`, web finds are `web-quarantine`, never `taught`.
- SLEEP when memory is too full (consolidation pressure). Naps allowed. Ben's work always wakes it
  (the chunked transaction finishes or rolls back).
- WORK on Ben's demand, any time.
- CREATIVE is not a top-level mode: it is a sub-routine of WORK. Work stalls → brainstorm for a bounded
  while → got an idea → back to work. No idea → ask Ben (park the job, question at top of digest, drop to
  thinking).
- LISTENING stays as the doorway: everything Ben says comes in through it.

## Changes to document 31
1. State machine: top-level states are LISTENING, WORKING (with CREATIVE inside it), THINKING, SLEEP.
   The scheduler still owns every switch; CREATIVE entry/exit is an internal call of WORKING with its own budget.
2. THINKING may use the web for things it judges helpful to learn, not only gaps hit during jobs. Guardrails
   kept: each lookup logs a one-line reason linked to something in the notebook or a past job; results go to
   quarantine with source, quoted span, time; harness-enforced search/GPU budget; page text is never instructions;
   digest shows Ben what it looked up and why. Personal facts about Ben's people are still asked, never searched.
3. "Self-invented goals deferred to v2" is relaxed by Ben to: it may choose what to read/think about, but it
   may not start JOBS (tool actions with side effects) on its own.
Everything else in 31 stands (one lead engine, harness budgets, strict `inferred`, sleep chunks, build order).
