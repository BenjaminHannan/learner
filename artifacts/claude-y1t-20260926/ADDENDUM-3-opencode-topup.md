# y1t addendum 3: the GLM top-up through Ben's opencode route (Answering-from-memory thread, 2026-09-26 19:38 UTC, before any item is read or judged)

**Why:** ADDENDUM-2's rule, applied to the Mac job's counts (origin/builder-outbox ef902c146,
artifacts/claude-y1t-20260926/glm/RESULTS-mac.md):
- 1,021 of 2,400 dialogs were tried before the 120-minute cap; 645 came back parsed, 376 failed (OpenRouter
  "402 Payment Required"), 1,379 were never started. The four logs have 683, 603, 548 and 634 lines naming 402.
- items_train.jsonl has 566 items and items_dev.jsonl has 102. 566 is under ADDENDUM-2's 1,500, so the missing
  dialogs are written through Ben's opencode route (GLM 5.3 Flash, Ben 18:47 UTC).
- The first run's cost, summed from the parsed rows' usage fields, is $0.3677 of OpenRouter credit (the workers died
  before printing totals).

**Checked here before this addendum (counts only, no item text read):**
- The seeds regenerate exactly: claude_lis320_seed.py with the Mac job's step-2 command prints the same counts and
  gives sha256 42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43 under two different hash seeds; all
  1,021 raw dialog ids are in it.
- lis-320's check and y1t's items step, re-run here on the Mac's raw.jsonl and those seeds, give the same counts and
  byte-identical items_train.jsonl (1b533502…) and items_dev.jsonl (de87a142…) and drops.jsonl.
- `claude_y1t_topup.py split` keeps the 645 parsed rows (raw_ok.jsonl, sha256 bed93883…) and lists 1,755 dialogs to
  redo (seeds_redo.jsonl, sha256 e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b).

**Rule (fixed now):**
1. Only the 1,755 dialogs in seeds_redo.jsonl are worded again; no parsed dialog is redone.
2. Route: scripts/claude_lis320_glm_oc.py (Reading facts' wrapper: same prompt, parser and rows as
   claude_lis320_glm.py; each call through the Director's helper scripts/claude_glm_opencode.py, sha256 3b597086…).
   Rows record model "opencode-go/glm-5.3-flash" and temperature null; the first run's rows say
   "z-ai/glm-5.3-flash" at OpenRouter's settings. Both are GLM 5.3 Flash; the mix is a disclosed deviation.
3. The Mac job (handoff/queue/y1t-topup-mac.md) runs in time-capped batches; a stopped run is resumed by a second job
   from its own output (rows already written are skipped).
4. This thread merges in the cloud: `claude_y1t_topup.py merge` (raw_ok + new rows, one row per dialog, parsed
   preferred), then lis-320's check and y1t's items step unchanged, into artifacts/claude-y1t-20260926/glm2/.
   The items step draws its dev split again over all the combined dialogs (seed 4027, 15% of dialogs), so a
   first-run dialog may move between train and dev; nothing has been trained on, judged or read, so this is harmless.
5. The data gate (GATE-data.md) runs on glm2's items_train.jsonl, with its sealed marks and seed.
   benspc-y1t (and y1r) then read glm2's items instead of glm's; nothing else in PLAN.md changes.
6. If the combined set still has fewer than 1,500 training items after every redo dialog has had one try, y1t goes on
   with what exists (the drafts step's repeat to 1,500 rows handles it), disclosed as a deviation. No third route.
