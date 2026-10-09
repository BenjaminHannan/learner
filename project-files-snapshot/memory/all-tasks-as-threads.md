---
name: all-tasks-as-threads
description: Ben's rule (2026-09-28 20:54 UTC): every helper task, check and recount runs as its own project thread, no Agent subagents
metadata:
  type: feedback
---

Ben: "you should run each task as a thread." Director sends each brief + short title to the coordinator session (session_01K1oN49HUGrchTKBS7h7jiQ) via send_message; coordinator starts the thread and returns the thread id. Applies to helpers, claim checks and blind recounts. Max 4 at once.
**Why:** he wants to see the work as visible threads.
**How to apply:** commit the brief under handoff/director-briefs/ and point the thread at it (see thread-helper-common.md). Read results with fetch_thread. A "Brainstorm next problems" thread may send Ben's picks. See [[director-role-and-rules]].

**Update 21:11 UTC:** Ben talks only to the coordinator; Director sends questions (one, short options, recommendation) to the coordinator by send_message, never asks in-thread. Rule also in handoff/director-briefs/thread-helper-common.md.

**Update 21:13 UTC (Ben):** every new task must be run by Ben first, with an eli5 artifact (handoff/kit/eli5) and must be one sub-problem of the problem being worked on or research for it. Send coordinator: title, brief on main, artifact link, one line on the problem served; thread starts only after his yes. Explainer build: compose title+eli5-head.css+cards, run check.js, publish. H10 page M472hGjn1A4ZEbmtprcsiz, H12 page AR4T9ie8kbYSTR6rqiGbNE.
