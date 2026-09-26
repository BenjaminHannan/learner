# lis-320 ADDENDUM-2: GLM wording through Ben's opencode route (written before any opencode-route row exists)

Written 2026-09-26 19:14 UTC by the reading thread. At this time no lis-320 row has been worded through opencode, and the
sealed test panel (claude-readpanel320) has not been read by any reader.

## Why
The full wording run (handoff/queue/lis320-full-mac.md, seed 322, 6000 dialogs) stopped at 18:38 UTC at 298 of 6000
dialogs: 60 calls failed four times with OpenRouter "402 Payment Required" (account out of funds). Nothing was pushed.
Ben (18:47 UTC) offered GLM 5.3 Flash through his opencode subscription; the Director's probe
(artifacts/claude-glm-opencode-20260926/REPORT.md on builder-outbox) got 15 of 15 calls back at 1, 2, 4 and 8 at once, and
wrote the shared helper scripts/claude_glm_opencode.py (sha256 3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2).

## The one change
The teacher route. Same model family (GLM 5.3 Flash), same prompt (claude_lis320_glm.build_prompt), same seeds script and
flags, same code checks, same builder, same training args, same marks R1-R7 and validity counts (PASSMARKS.md,
ADDENDUM-1), same sealed test panel. New file scripts/claude_lis320_glm_oc.py calls the helper instead of OpenRouter;
claude_lis320_glm.py is not edited (Answering from memory's y1t seals it).
What the route changes that I cannot set: temperature (OpenRouter run: 1.0; opencode: its default), reasoning effort
(OpenRouter: low; opencode: its default), max tokens (8000 vs its default), and opencode may add its own system text.
Rows record model "opencode-go/glm-5.3-flash" and temperature null.

## Pilot 3 before the full run (fixed now)
Seed 321, 60 dialogs, the exact pilot 2 seeds command, through the new route with 4 calls at once. The six thresholds in
PILOT-THRESHOLDS.md apply unchanged (item 6, cost, is $0 on this route). Two added checks for the route itself:
- parsed dialogs at least 54 of 60 (pilot 2 on OpenRouter: 60 of 60 called, 390 of 425 turns kept);
- failed calls (empty after the helper's 3 tries) at most 3 of 60.
If none trigger, the full run goes ahead on this route with the same prompt and checks. If any trigger, I change one thing,
say what, and re-pilot on seed 323 before any full run. Pilot 3 also gives the calls-per-minute figure that sizes the chunks.
The pilot 2 result stays evidence for the OpenRouter route only.

## Full run
- Seeds: seed 322, 6000 dialogs, the same command as the stopped run (re-created by code).
- The 298 OpenRouter rows from the stopped run are not used, so every training row comes from one route.
- Chunks: each Mac job runs claude_lis320_glm_oc.py with --max-minutes 160 (inside its 180-minute cap) and resumes from the
  raw rows the previous chunk pushed (raw.part.jsonl.gz). A chunk stops early after more than 50 failed calls and reports.
- Size: target all 6000 dialogs; floor 3000 dialogs called. If the route slows so much that 6000 is out of reach, the run
  stops at the first chunk boundary at or above 3000 only on the Thread manager's say-so. The final dialog count, kept
  rows and family mix go into DATA.md before training (PASSMARKS: the data size is fixed after the pilot, not a second change).
- Then: a blind or hand sample check of kept rows (hygiene rule 2, counts kept in the report), and the BensPC job
  handoff/held/lis-320-benspc.md, unchanged except for the raw file it rebuilds from.

## Report-only GLM panel
PASSMARKS' second report-only panel was "a different prompt and temperature 0.7". This route cannot set temperature, so
that panel differs from training by prompt only. It has no bar either way.

## Cost
$0 in money: Mac CPU and Ben's opencode subscription (no plan needed under Ben's 18:54 UTC rule); training on BensPC.
