Starting the Luna pilot — setting up the isolated run.
Isolated tree ready — now verifying the seals.
Seals and self-tests passed — starting the 40 answer rewrites.
Answers complete and route filter clean — now generating the new practice chats.
All generations finished — packaging the outputs for handoff.
Files verified — now writing the final report.
Temp workspace cleaned — confirming the deliverables.
RAN

origin/main: 91e5d89cb17dd89cb9071c4f429d237f55db51ee
label: k1h-luna-pilot

integer counts:
- seals: 25 OK, 2 OK, 4 OK, 5 OK, 3 OK, 5 OK (all exit 0)
- selftests: 8/8, 3/3, 2/2
- answers tries: 40 total, 40 kind=ok, 0 other kinds
- answers secs ok: 40 n, median 7.55, max 26.4
- answers.jsonl: 40 lines, 40 nonempty, 0 empty, 40 distinct item_id, 0 CRLF
- answers_filtered.jsonl: 40 lines, 40 nonempty, 0 empty, 40 distinct item_id, 0 CRLF
- chats tries: 2 total, 2 kind=ok
- chats.jsonl: 37 lines, 37 distinct item_id, 0 CRLF
- Luna calls: 42 total (40 answers + 2 chats)

seals (from $D):
- SEAL-k1h.sha256.txt: 25 OK
- SEAL-addendum1.sha256.txt: 2 OK
- SEAL-addendum2.sha256.txt: 4 OK
- SEAL-addendum3.sha256.txt: 5 OK
- SEAL-addendum4.sha256.txt: 3 OK
- SEAL-addendum5.sha256.txt: 5 OK

selftests:
- k1h luna selftest 8/8 ok
- k1h glm selftest 3/3 ok
- k1h routefilter selftest 2/2 ok

step 4 ANSWERS (05:15:09 to 05:21:10 UTC 2026-09-27, exit 0):
- last line: {"items": 40, "already": 0, "answered": 40, "failed": 0, "not_started": 0, "minutes": 6.0, "stopped_early": false}
- kind_ok=40, try_total=40, median_secs=7.55, max_secs=26.4

step 5 ROUTE FILTER (05:21:21 UTC, exit 0):
- {"rows": 40, "nonempty_in": 40, "route_loss_rows": 0, "by_rule": {}, "items_hit": 0, "nonempty_out": 40, "repeated_texts": 0}

step 6 CHATS (05:21:27 to 05:24:44 UTC, exit 0):
- {"chats": 37, "mix": {"idea1": 14, "idea0": 14, "uf1": 3, "uf2": 3, "uf3": 3}, "rejected": {"bad: fact value not in teach turns": 3}, "calls": 2, "failed_calls": 0}
- {"luna_chats_renamed": 37}
- kind_ok=2, try_total=2

step 7 COUNTS:
- answers.jsonl: lines=40 nonempty=40 empty=0 distinct=40 crlf=0 error_kinds=none
- answers_filtered.jsonl: lines=40 nonempty=40 empty=0 distinct=40 crlf=0 error_kinds=none
- chats.jsonl: lines=37 distinct=37 crlf=0

times UTC 2026-09-27: seals 05:14:52, selftests 05:14:57, answers 05:15:09-05:21:10, routefilter 05:21:21, chats 05:21:27-05:24:44, counts 05:25:02, report 05:25:38

copies sha256 match ($O vs pilot/):
- answers.jsonl 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603
- answers_filtered.jsonl 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603
- answer-log.txt d5dff824d11df143ec841f45eb9ad65c92a8ef19ea0e547e02d8ffcf0a7547b0
- chats.jsonl 745b4377a44f0716155ba7d655c7d768f90547b0abc80214adb5e9d5845537e5
- chats-log.txt 641fed48f816cb906b933c40c84ca821206b9567bc413693c138c494a350d0e1
- force-added 6 files in artifacts/claude-k1h-20260926/luna/pilot/
- $D removed, confirmed gone

errors: none
deviations: none. Observed: git fetch/archive only, run from $D, uv run --offline --no-project --python 3.12 python -B stdlib only, workers 1, 1 at a time via claude_luna_codex.py, $0, no GLM/opencode/rental/BensPC/OpenRouter, LOAD-LIGHT yes, GPU no, TIME CAP 90 min (used ~10 min), additive only, no secrets, never wrote notebook/, never checkout/push, never quoted chat/answer, never edited thread code.

PUSH: artifacts/claude-k1h-20260926/luna/pilot
