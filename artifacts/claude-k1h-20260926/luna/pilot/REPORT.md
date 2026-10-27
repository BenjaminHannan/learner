# k1h Luna pilot REPORT

verdict: RAN

origin/main commit: 91e5d89cb17dd89cb9071c4f429d237f55db51ee

label: k1h-luna-pilot

## Times (UTC 2026-09-27)

- tree fetch/archive: fetch exit 0 before 05:14:52; archive exit 0; rev-parse recorded 05:14 (fetch step)
- seals check: 05:14:52
- selftests: 05:14:57 to 05:14:57
- answers start: Sun Sep 27 05:15:09 UTC 2026
- answers end: Sun Sep 27 05:21:10 UTC 2026
- routefilter: Sun Sep 27 05:21:21 UTC 2026
- chats start: Sun Sep 27 05:21:27 UTC 2026
- chats end: Sun Sep 27 05:24:44 UTC 2026
- counts: Sun Sep 27 05:25:02 UTC 2026
- report written: Sun Sep 27 05:25:38 UTC 2026

## Seals (run from $D; shasum -a 256 -c)

- artifacts/claude-k1h-20260926/SEAL-k1h.sha256.txt: 25 OK, exit 0
- artifacts/claude-k1h-20260926/SEAL-addendum1.sha256.txt: 2 OK, exit 0
- artifacts/claude-k1h-20260926/SEAL-addendum2.sha256.txt: 4 OK, exit 0
- artifacts/claude-k1h-20260926/SEAL-addendum3.sha256.txt: 5 OK, exit 0
- artifacts/claude-k1h-20260926/SEAL-addendum4.sha256.txt: 3 OK, exit 0
- artifacts/claude-k1h-20260926/SEAL-addendum5.sha256.txt: 5 OK, exit 0
- full per-file OK listings verified in $O/seal_*_out.txt during run; all lines OK, zero failures

## Selftests (uv run --offline --no-project --python 3.12 python -B; no network)

- scripts/claude_k1h_luna.py selftest: k1h luna selftest 8/8 ok (exit 0)
- scripts/claude_k1h_glm.py selftest: k1h glm selftest 3/3 ok (exit 0)
- scripts/claude_k1h_routefilter.py selftest: k1h routefilter selftest 2/2 ok (exit 0)

## Step 4 ANSWERS

command: scripts/claude_k1h_luna.py answer --items artifacts/claude-k1h-20260926/luna/pilot_items.jsonl --out $O/answers --workers 1 --cap-minutes 45 > $O/answer-log.txt 2>&1
exit: 0

last line of answer-log.txt verbatim:
{"items": 40, "already": 0, "answered": 40, "failed": 0, "not_started": 0, "minutes": 6.0, "stopped_early": false}

[k1h-luna-try] lines by kind:
- kind_ok=40
- try_total=40

secs over kind=ok lines:
- median_secs=7.55
- max_secs=26.4
- ok_n=40

## Step 5 ROUTE FILTER

command: scripts/claude_k1h_routefilter.py --answers $O/answers/answers.jsonl --out $O/answers/answers_filtered.jsonl
exit: 0

printed line verbatim:
{"rows": 40, "nonempty_in": 40, "route_loss_rows": 0, "by_rule": {}, "items_hit": 0, "nonempty_out": 40, "repeated_texts": 0}

## Step 6 CHATS

command: scripts/claude_k1h_luna.py chats --existing artifacts/claude-k1e-20260926/train/items.jsonl --out $O/chats --calls 2 --chunk p --workers 1 --cap-minutes 20 > $O/chats-log.txt 2>&1
exit: 0

lines of chats-log.txt starting with "{" verbatim:
{"chats": 37, "mix": {"idea1": 14, "idea0": 14, "uf1": 3, "uf2": 3, "uf3": 3}, "rejected": {"bad: fact value not in teach turns": 3}, "calls": 2, "failed_calls": 0}
{"luna_chats_renamed": 37}

[k1h-luna-try] lines by kind:
- kind_ok=2
- try_total=2

## Step 7 COUNTS (script printing counts only; no chat/answer quoted)

- answers.jsonl: lines=40 nonempty_answer=40 empty_answer=0 distinct_item_id=40 crlf_bytes=0
- answers.jsonl: error_kinds=none
- answers_filtered.jsonl: lines=40 nonempty_answer=40 empty_answer=0 distinct_item_id=40 crlf_bytes=0
- answers_filtered.jsonl: error_kinds=none
- chats.jsonl: lines=37 distinct_item_id=37 crlf_bytes=0

## Copies sha256 ($O vs worktree pilot/)

- answers.jsonl: 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603 (match)
- answers_filtered.jsonl: 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603 (match)
- answer-log.txt: d5dff824d11df143ec841f45eb9ad65c92a8ef19ea0e547e02d8ffcf0a7547b0 (match)
- chats.jsonl: 745b4377a44f0716155ba7d655c7d768f90547b0abc80214adb5e9d5845537e5 (match)
- chats-log.txt: 641fed48f816cb906b933c40c84ca821206b9567bc413693c138c494a350d0e1 (match)

pilot files: answers.jsonl, answers_filtered.jsonl, answer-log.txt, chats.jsonl, chats-log.txt, REPORT.md in artifacts/claude-k1h-20260926/luna/pilot/

## Errors and deviations

- errors: none. answer exit 0, routefilter exit 0, chats exit 0. seals all OK. selftests all OK.
- deviations: none.
- constraints observed: LOAD-LIGHT yes; GPU no (Mac CPU); 42 Luna calls total (40 answers + 2 chats, each 1 try, workers 1, 1 at a time via scripts/claude_luna_codex.py; $0); no GLM, no opencode command, no rental, no BensPC, no OpenRouter; label k1h-luna-pilot; TIME CAP 90 minutes (used ~10 minutes 05:14:52 to 05:24:44); DISK 1 ($D only plus pilot copies); PYTHON uv run --offline --no-project --python 3.12 python -B standard library only, installed nothing; CODEX RULES observed (never read/printed/copied/committed ~/.codex or key/auth files; helper sandbox unchanged); additive only, fictional names, no secrets, never wrote to repo-root notebook/; never checked out or pushed a branch; never opened/printed/quoted a chat or an answer (counts-only parsing); never edited thread code (run only); used git fetch -q origin main and git archive origin/main (never worktree scripts).
