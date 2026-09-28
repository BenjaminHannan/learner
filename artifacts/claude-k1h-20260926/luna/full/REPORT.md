# k1h-luna-full REPORT

verdict: RAN

label: k1h-luna-full
machine: Mac CPU (no GPU), LOAD-LIGHT
helper: scripts/claude_luna_codex.py via scripts/claude_k1h_luna.py, workers 1, 1 call at a time
cost: $0

## origin/main commit

- archive commit (git rev-parse origin/main at tree setup, 2026-09-27T06:43:13Z): 756fdd302b301a58c6cec6f55d4c36db91c6dea6
- earlier fetch at 2026-09-27T06:42:32Z showed 6a62dcae4e3951bf33e1b25f20a3ab6af8216b89; origin/main moved between fetches (see deviations).

## duplicate guard (before anything else)

- 2026-09-27T06:42:19Z worktree branch: claude/card-experiment-handoff-7c5b27 (not main, as required)
- git ls-tree --name-only origin/main -- artifacts/claude-k1h-20260926/luna/full: empty (no output)
- git ls-tree --name-only origin/builder-outbox -- artifacts/claude-k1h-20260926/luna/full: empty
- origin/main luna dir contained only: pilot-score, pilot, pilot_items.jsonl
- origin/builder-outbox luna dir contained only: pilot
- ps check (ignore opencode lines, exclude grep): no running python/uv process with claude_k1h_luna.py in args. Other luna scripts running (different tasks) do not match. Result: no-luna-procs-after-filter.
- verdict: not a duplicate, proceeded.

## tree (step 1)

- 2026-09-27T06:43:04Z: git fetch -q origin main (exit 0); mktemp -d -> /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.08G1HFx4hV (recorded as D)
- git archive origin/main scripts artifacts/claude-k1e-20260926/train/items.jsonl artifacts/claude-k1h-20260926 artifacts/claude-k1f-20260926 artifacts/claude-k1fpanel-20260926/SEAL.sha256.txt | tar -x -C $D (exit 0)
- O=$D/O; mkdir -p $O/answers $O/chats
- K=artifacts/claude-k1e-20260926/train/items.jsonl (240 lines)
- G=artifacts/claude-k1h-20260926/glm/chats.jsonl (593 lines)
- P=artifacts/claude-k1h-20260926/luna/pilot/answers.jsonl (40 lines)

## seals (step 2, run from $D)

- 2026-09-27T06:43:19Z: shasum -a 256 -c artifacts/claude-k1h-20260926/SEAL-k1h.sha256.txt -> 25 OK, exit 0
- 2026-09-27T06:43:28Z:
  - SEAL-addendum1.sha256.txt -> 2 OK, exit 0
  - SEAL-addendum2.sha256.txt -> 4 OK, exit 0
  - SEAL-addendum3.sha256.txt -> 5 OK, exit 0
  - SEAL-addendum4.sha256.txt -> 3 OK, exit 0
  - SEAL-addendum5.sha256.txt -> 5 OK, exit 0
- 2026-09-27T06:43:30Z: shasum -a 256 $G $P:
  - 49c74254ea797454d98967b4b3123f23f51498ae8e70089ff978191db76ee8a2 for G (matches expected)
  - 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603 for P (matches expected)
- wc -l < $G = 593 (matches expected)
- wc -l < $P = 40; wc -l < $K = 240

## selftests (step 3, no network)

- 2026-09-27T06:43:34Z, all via `uv run --offline --no-project --python 3.12 python -B`:
  - scripts/claude_k1h_luna.py selftest -> "k1h luna selftest 8/8 ok" (exit 0)
  - scripts/claude_k1h_glm.py selftest -> "k1h glm selftest 3/3 ok" (exit 0)
  - scripts/claude_k1h_routefilter.py selftest -> "k1h routefilter selftest 2/2 ok" (exit 0)

## chats (step 4)

- command: scripts/claude_k1h_luna.py chats --existing $K --existing $G --out $O/chats --calls 7 --chunk a --workers 1 --cap-minutes 50 > $O/chats-log.txt 2>&1
- start: Sun Sep 27 06:43:45 UTC 2026 (also recorded 2026-09-27T06:43:42Z pre-check)
- end: Sun Sep 27 07:05:25 UTC 2026 (exit 0)
- $O/chats/chats.jsonl exists, 53769 bytes, 138 lines
- every line of chats-log.txt starting with "{" verbatim (counts only, no chat content):
  - {"chats": 138, "mix": {"idea1": 49, "idea0": 49, "uf1": 13, "uf2": 13, "uf3": 14}, "rejected": {"bad: fact value not in teach turns": 2}, "calls": 7, "failed_calls": 0}
  - {"luna_chats_renamed": 138}
- [k1h-luna-try] lines by kind=: 7 kind=ok, 0 other kinds
- secs stats over kind=ok (chats): n=7, min 125.9, median 187.9, max 273.6

## answers (step 5)

- cp $P $O/answers/answers.jsonl at 2026-09-27T07:05:38Z (exit 0); verified 40 lines, sha256 8cfbc62d8a955935c0b6bcaddb4cf5720b749aaca5edc297867a871d0f9cc603
- includes --items $O/chats/chats.jsonl (chats existed)
- total items: 971 = 240 + 593 + 138

- chunk 1:
  - start: Sun Sep 27 07:05:41 UTC 2026
  - end: Sun Sep 27 08:05:42 UTC 2026 (exit 0)
  - last line verbatim: {"items": 971, "already": 40, "answered": 286, "failed": 0, "not_started": 645, "minutes": 60.0, "stopped_early": true}
  - answers.jsonl lines after: 326

- chunk 2:
  - start: Mon Sep 28 00:00:02 UTC 2026
  - end: Mon Sep 28 01:00:03 UTC 2026 (exit 0)
  - last line verbatim: {"items": 971, "already": 326, "answered": 361, "failed": 0, "not_started": 284, "minutes": 60.0, "stopped_early": true}
  - answers.jsonl lines after: 687

- chunk 3:
  - start: Mon Sep 28 01:00:22 UTC 2026
  - end: Mon Sep 28 01:44:31 UTC 2026 (exit 0)
  - last line verbatim: {"items": 971, "already": 687, "answered": 284, "failed": 0, "not_started": 0, "minutes": 44.1, "stopped_early": false}
  - answers.jsonl lines after: 971
  - stop reason: failed=0 and not_started=0 (every item answered); loop stopped, chunks 4-6 not run.

- [k1h-luna-try] over all answer chunks by kind=: 931 kind=ok (286 + 361 + 284), 0 other kinds
- secs over kind=ok answer tries: n=931, min 4.5, median 9.1, max 92.4

## route filter (step 6)

- 2026-09-28T01:44:42Z: scripts/claude_k1h_routefilter.py --answers $O/answers/answers.jsonl --out $O/answers/answers_filtered.jsonl (exit 0)
- printed line verbatim: {"rows": 971, "nonempty_in": 971, "route_loss_rows": 0, "by_rule": {}, "items_hit": 0, "nonempty_out": 971, "repeated_texts": 0}

## counts (step 7, script prints counts only, no chat/answer quoted)

- answers.jsonl: lines=971, nonempty_answer=971, empty_answer=0, error_by_kind={}, distinct_item_id=971, distinct_item_id_nonempty=971, nonempty_by_prefix={'kt-': 240, 'kh-': 593, 'kl-': 138}, crlf_bytes=0
- answers_filtered.jsonl: lines=971, nonempty_answer=971, empty_answer=0, error_by_kind={}, distinct_item_id=971, distinct_item_id_nonempty=971, nonempty_by_prefix={'kt-': 240, 'kh-': 593, 'kl-': 138}, crlf_bytes=0
- chats.jsonl: lines=138, distinct_item_id=138, crlf_bytes=0

## copies (step 8)

- destination: artifacts/claude-k1h-20260926/luna/full/ (new; worktree already contained full-r1, full-r2, full-r3 and pilot, untouched)
- 2026-09-28T01:45:19Z source sha256:
  - chats.jsonl e90e866649e64e56b3476721b8f607863d2aed5a167b48b4e3d73f2b710cefdb
  - chats-log.txt 5031d69b4895a37f3b9778d389fa19712948ed4502f884de341e22e325a53cf3
  - answer-log-1.txt 00879d3b288b39bc1cfd556cb6f17b11f84f61d2145c570a902a4ce3132bb82b
  - answer-log-2.txt 9007b6335fd67096f725d9f64c977d5edb297770b4f9bd25fa3d9385d9d8c1db
  - answer-log-3.txt 424d46c3803bca229684d3b10a0abcc153a8db75ebe66a2e52e30517d97c7d91
  - answers.jsonl cdf2c50bc8d0a52109b8772cced8c2ed6a07477a14671ae4e3aedd5dbf8a1aa1
  - answers_filtered.jsonl cdf2c50bc8d0a52109b8772cced8c2ed6a07477a14671ae4e3aedd5dbf8a1aa1
- all 7 copies verified byte-identical (sha256 match after copy).
- files copied: answers.jsonl, answers_filtered.jsonl, chats.jsonl, chats-log.txt, answer-log-1.txt, answer-log-2.txt, answer-log-3.txt, plus this REPORT.md
- force-add required (artifacts/ is git-ignored); push is left to watcher per task (never checked out or pushed a branch here).

## times (UTC)

- duplicate guard: 2026-09-27T06:42:19Z, 06:42:32Z, 06:42:33Z
- tree: 2026-09-27T06:43:04Z, 06:43:13Z
- seals: 2026-09-27T06:43:19Z, 06:43:28Z, 06:43:30Z
- selftests: 2026-09-27T06:43:34Z
- chats: 2026-09-27T06:43:42Z pre-check; 06:43:45Z start; 07:05:25Z end; 07:05:31Z verify
- answers cp: 2026-09-27T07:05:38Z
- answer chunk 1: 2026-09-27T07:05:41Z to 2026-09-27T08:05:42Z
- answer chunk 2: 2026-09-28T00:00:02Z to 2026-09-28T01:00:03Z; verify 01:00:19Z
- answer chunk 3: 2026-09-28T01:00:22Z to 2026-09-28T01:44:31Z
- route filter + counts: 2026-09-28T01:44:42Z to 2026-09-28T01:45:19Z
- copies: 2026-09-28T01:45:22Z and 2026-09-28T01:45:xxZ

## errors and deviations

1. origin/main moved during setup: first rev-parse 6a62dcae4e3951bf33e1b25f20a3ab6af8216b89, archive commit 756fdd302b301a58c6cec6f55d4c36db91c6dea6. Used the latter for the whole run. No seal impact (all OK).
2. TIME CAP exceeded on wall clock: task cap 7h30m from 2026-09-27 05:50 UTC = deadline ~13:20 UTC 2026-09-27. Chats + chunk 1 finished by 08:05 UTC (within cap). Long pause (~16h) occurred between chunk 1 end (08:05:42Z Sep 27) and chunk 2 start (00:00:02Z Sep 28); chunks 2-3 therefore ran Sep 28, past the deadline. Compute used: chats ~22m + answers 60 + 60 + 44.1 = ~186m (~3h06m) plus selftests/seals, well under 7h30m of compute; wall clock exceeded due to the pause. Final completion still satisfies the stop condition (failed 0, not_started 0). No data loss.
3. No other errors: all seals OK, all selftests exact, chats exit 0, all 3 answer chunks exit 0, routefilter exit 0, counts exit 0, all sha256 matches, CRLF counts 0 as expected, no empty answers, route_loss_rows 0.
4. No chat or answer content opened, printed, quoted, or committed beyond counts. Scripts run only via `uv run --offline --no-project --python 3.12 python -B` with stdlib only; nothing installed; every shell command kept under 70 minutes (chats 50 cap, answers 60 cap). No read/print/copy/commit of ~/.codex or keys. No GPU, no GLM, no opencode command, no rental, no BensPC, no OpenRouter. Worktree branch never changed; no checkout/push by this job. Additive only under artifacts/claude-k1h-20260926/luna/full/; repo-root notebook/ untouched.

## integer counts summary

- chats calls: 7
- chats lines: 138
- answer items total: 971
- pilot answers reused: 40
- chunk answers: 286 + 361 + 284 = 931
- answer try lines ok: 931
- answers.jsonl lines: 971
- answers_filtered.jsonl lines: 971
- distinct item_ids answered: 971
- empty answers: 0
- route_loss_rows: 0
- failed items final: 0
- not_started final: 0
