# y1t addendum 5: GPT-6 Luna words the last 315 dialogs (Answering-from-memory thread, DRAFT 2026-09-27 03:49 UTC, OK'd by the Thread manager 03:50 UTC; runner and L3 mechanics added 03:51 UTC; sealed 03:53 UTC in SEAL-y1t-add5.sha256.txt after the Director's live helper check; no Luna call has been made by this thread)

**Why:** Ben, 03:47 UTC (goals page, cd475e141 and 5ed7dcad9): "just have luna rewrite all the training data. It's so so
cheap". A sealed experiment keeps its writer unless an addendum switches it, with a small quality pilot first. The
last 315 of the 1,755 redo dialogs wait on Ben's opencode plan, which has been over its usage limit since about 00:57
UTC (ADDENDUM-3 route update 3).

**What changes (one thing):** the writer of those 315 dialogs only (seeds_redo.jsonl, the 315 not in
topup/raw_new.jsonl, in seeds_redo order). They are worded by GPT-6 Luna through Ben's Codex plan, via the Director's
Luna text-call helper (a new file, named here when it is committed; its probe must pass first). Everything else is
unchanged: the same prompt (claude_lis320_glm.build_prompt), parser, batches and rows (claude_lis320_glm_oc.run_batches),
one try per dialog, and the route-loss filter (ADDENDUM-4) before any merge. Rows record Luna's model id.
- Kept as they are: the first run's 645 rows (GLM via OpenRouter) and the top-up's 1,440 (GLM via opencode), including
  its 80 unparsed rows, which had their one try. Nothing already written is redone.
- Nothing is Claude-written or Claude-judged for training (Ben 16:39). Claude's blind judges still only decide whether
  the data is used (GATE-data.md), as sealed.
- The mix of writers (GLM for 2,085 dialogs, Luna for up to 315) is a disclosed deviation. Items keep their dialog id,
  so every result can be split by writer (report only).

**Pilot, marks fixed now (before any Luna call):** the first 60 of the 315, run through the new runner.
- L1, route: at most 3 of 60 rows dropped by the route-loss filter (empty, error text, or a text given 3+ times).
- L2, parse: at least 54 of 60 parsed (90%; the GLM top-up parsed 1,360 of 1,440, 94%).
- L3, the data gate's own blind questions on the pilot's items: lis-320's check and y1t's items step (unchanged) on the
  60 pilot dialogs, then the G1b filter; every answerable pilot item goes to G2 and G3 exactly as GATE-data.md runs them
  (two fresh blind judges, a third on disagreements; the first line of every judge prompt says never use WebFetch).
  PASS if each of G2 and G3 misses at most 10% of those items, rounded down (the sealed 54 of 60 rate).
- Report only: lis-320 check drop counts and kept-turn share next to the GLM top-up's.
- Pilot PASS (L1, L2 and L3): the other 255 are worded by Luna with the same runner, then the route filter, the merge
  (ADDENDUM-3 rule 4) and the full data gate (GATE-data.md with GATE-ADDENDUM-1) as sealed. The 60 pilot rows are kept.
- Pilot FAIL: Luna is not used for y1t and its 60 rows are left out. The 315 wait for GLM (ADDENDUM-3), or ADDENDUM-4's
  fallback applies when BensPC is ready.
- Proved wrong: the Luna pilot fails L2 or L3, which would mean the lis-320 prompt does not carry over to Luna as is.

**Runs where:** on the Mac as a watcher job (Codex is Ben's plan there), $0 extra, no BensPC, no rental. Job file
handoff/held/y1t-luna-pilot-mac.md, queued only after the helper's selftest passes and this addendum is sealed.

**Code (written 03:51 UTC; no Luna call made):**
- Helper: the Director's scripts/claude_luna_codex.py (24ca7a163): call(text, model="gpt-6-luna", timeout) -> str;
  an empty or error-like reply raises instead of being returned. sha256 342a0fb7…024e, pinned in the seal. The Director's
  live check on the Mac (03:54 UTC by the Director's clock): selftest ok, 3 parallel calls in 10.9 s. y1t's share of the
  Luna route: 3 parallel calls of 12.
- Runner: scripts/claude_y1t_luna.py. `pick` writes the redo seeds with no row in topup/raw_new.jsonl, in order (315
  here; sha256 of that file 6184cd22…83de). The run is Reading facts' run_batches with Luna's call; rows record model
  "codex/gpt-6-luna", temperature null. A failed call writes a row with empty "raw", which the route filter drops (L1).
  Selftest ok with a stubbed helper (no network).
- L3 mechanics: claude_y1t_gate.py sample --n 1000 --seed 4034 on all pilot items (so every answerable pilot item is
  judged), then splits and score as sealed. Only score's asks_yes and stated_yes counts are used; its G2/G3 booleans
  (fixed at 54 of 60) do not apply to the pilot. L3 passes if asks_yes and stated_yes are each at least
  items - floor(0.10 x items).
