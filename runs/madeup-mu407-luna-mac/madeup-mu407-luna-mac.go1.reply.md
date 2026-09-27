Doing your queued prep run — starting the sealed write.
Tree set up — now verifying the seals.
Seals and facts ready — firing the pilot write.
Pilot passed — full write is underway, polling it.
Over halfway there — continuing the watch.
Checks passed — packaging the results.
Results filed — cleaning up the temp tree.
Verdict: DONE — pilot PASS, full write 78/78, checks pass.

Report (additive only, fictional names only, no TEST-ONLY panel read):

- origin/main used: `6c90c5e71209353dd26724b7e558abb90ed5473b`; origin/main at end: `e49be974d0cc4ac5b04e2ec112dd1e2cfcb5efa9` (moved mid-run, work stayed on 6c90c5e)
- label: madeup-mu407-luna; GPU: no; workers 1
- TREE: fetch EXIT 0, archive EXIT 0, prep dir made
- SEAL-prep: 7/7 OK, EXIT 0
- SEAL-luna: 3/3 OK, EXIT 0
- SELFTESTS: `selftest-luna` printed timeout JSON + `mu407 prep-luna selftest 11/11 ok` EXIT 0; `selftest` `mu407 prep selftest 8/8 ok` EXIT 0; `luna_codex --selftest` `selftest ok: model gpt-6-luna, output-file True` EXIT 0
- PILOT:
  - facts: `{"rows":78,"smoke":3}` EXIT 0
  - smokefacts: `{"smoke_rows":3}` EXIT 0
  - frames: `{"ok":true,"attempts":1,"chars":{"system":576,"memory_header":46,"line_prefix":14,"current_label":22}}` EXIT 0
  - pilot write: `[mu407w] 3/3 written, 3 ok` + `{"rows":3,"ok":3,"errors":{},"stopped":"done","minutes":0.9}` EXIT 0
  - pilot: `{"frames_ok":true,"smoke_rows":3,"smoke_ok":3,"scan_hits":{"usage limit":0,"rate limit":0,"error:":0,"as an ai":0,"openai":0,"codex":0,"i can't help with":0},"status":"PASS"}` EXIT 0 → pilot PASS, continued
- FULL WRITE: started 05:59:06 UTC PID 20339, finished 06:29:29 UTC, no kill needed
  - write.log: 12/75, 24/75, 36/75, 48/75, 60/75, 72/75, 75/75 + `{"rows":78,"ok":78,"errors":{},"stopped":"done","minutes":29.3}`
  - raw.jsonl: 78 lines
- SELECT: `{"panel":60,"smoke":3}` EXIT 0
- CHECK: `{"chats":63,"panel":60,"smoke":3,"session1_turns":189,"session2_turns":315,"problems":{}}` EXIT 0
- SCAN: `{"kept_chats":78,"scan_hits":{"usage limit":0,"rate limit":0,"error:":0,"as an ai":0,"openai":0,"codex":0,"i can't help with":0},"repeated_messages":26,"max_repeat":12}` EXIT 0
- COPIED to worktree `artifacts/claude-mu407-20260927/prep/` (counts only in RESULTS.md): facts_all 78, smoke_facts 3, frames.json, raw 78, write.log, panel/items 63, facts 63, RESULTS.md
- writer: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
- CLEANUP: `rm -rf /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.F9oczaqv8P` EXIT 0, confirmed gone
- MISSES/DEVIATIONS: none for task logic; only notes: selftest-luna prints an extra timeout JSON line before its ok line; origin/main advanced during run; worktree `artifacts/` is gitignored but files created as instructed for watcher
- What this means in plain English: the writer made 78 practice chats from code-picked facts, all finished, the 60+3 picked chats pass the format check, and the scan found no banned phrases. It does not mean the chats are good, only that they are ready for the next step.

PUSH: artifacts/claude-mu407-20260927/prep
