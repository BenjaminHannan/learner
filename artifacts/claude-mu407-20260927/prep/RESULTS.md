# mu-407 prep (Luna) RESULTS

- origin/main commit used: 6c90c5e71209353dd26724b7e558abb90ed5473b
- origin/main at end of run: e49be974d0cc4ac5b04e2ec112dd1e2cfcb5efa9 (moved during run; work used 6c90c5e)
- label: madeup-mu407-luna
- GPU: no (Mac CPU; Luna via scripts/claude_luna_codex.py, --workers 1)
- temp dir: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.F9oczaqv8P (removed at end)
- worktree prep dir: artifacts/claude-mu407-20260927/prep/
- verdict: pilot PASS, full write done, select/check/scan done

## uptimes
- Sun Sep 27 05:57:17 UTC 2026: 1:57 up 3 days, 15:50, load averages: 130.07 121.65 109.23
- Sun Sep 27 05:57:24 UTC 2026: 1:57 up 3 days, 15:50, load averages: 130.55 121.89 109.38
- Sun Sep 27 06:29:40 UTC 2026: 2:29 up 3 days, 16:22, load averages: 131.04 106.77 96.78
- Sun Sep 27 06:29:57 UTC 2026: 2:29 up 3 days, 16:23, load averages: 126.64 106.99 97.03

## date -u log
- 05:57:17 fetch/start
- 05:57:24 archive
- 05:57:28 prep mkdir
- 05:57:30 rev check
- 05:57:43 facts before
- 05:57:43 facts after
- 05:57:45 smokefacts before
- 05:57:45 smokefacts after
- 05:57:47 frames before
- 05:58:01 frames after
- 05:58:04 pilot-write before
- 05:59:00 pilot-write after
- 05:59:02 pilot-check before
- 05:59:02 pilot-check after
- 05:59:06 full-write start
- 05:59:10 poll alive
- 06:05:57 poll alive
- 06:10:41 poll alive
- 06:15:23 poll alive
- 06:20:04 poll alive
- 06:24:47 poll alive
- 06:29:29 full-write done
- 06:29:32 select before/after
- 06:29:34 check/scan
- 06:29:40 worktree check
- 06:29:57 final check

## 1. TREE
- `git fetch -q origin main` EXIT 0
- `git archive origin/main scripts artifacts/claude-mu407-20260927 | tar -x -C $D` EXIT 0
- `git rev-parse origin/main` = 6c90c5e71209353dd26724b7e558abb90ed5473b
- prep dir created: artifacts/claude-mu407-20260927/prep

## 2. SEAL (from $D)
- `shasum -a 256 -c artifacts/claude-mu407-20260927/SEAL-prep.sha256.txt` EXIT 0:
  - scripts/claude_mu407_prep.py: OK
  - scripts/claude_mu405_facts.py: OK
  - scripts/claude_lis320_glm_oclow.py: OK
  - scripts/claude_lis320_glm_oc.py: OK
  - scripts/claude_glm_opencode_v11.py: OK
  - scripts/claude_glm_leakcheck.py: OK
  - scripts/claude_mu405_check.py: OK
- `shasum -a 256 -c artifacts/claude-mu407-20260927/SEAL-luna.sha256.txt` EXIT 0:
  - artifacts/claude-mu407-20260927/ADDENDUM-1-luna.md: OK
  - scripts/claude_mu407_prep_luna.py: OK
  - scripts/claude_luna_codex.py: OK

## 3. SELFTESTS (EXIT 0 each)
- `scripts/claude_mu407_prep_luna.py selftest-luna`:
  - {"ok": false, "attempts": 3, "error": "luna call failed after 3 tries: timeout after 300s"}
  - mu407 prep-luna selftest 11/11 ok
  - EXIT 0
- `scripts/claude_mu407_prep_luna.py selftest`:
  - mu407 prep selftest 8/8 ok
  - EXIT 0
- `scripts/claude_luna_codex.py --selftest`:
  - selftest ok: model gpt-6-luna, output-file True
  - EXIT 0

## 4. PILOT
- `facts --out $O/facts_all.jsonl`:
  - {"rows": 78, "smoke": 3}
  - EXIT 0
- `smokefacts --facts $O/facts_all.jsonl --out $O/smoke_facts.jsonl`:
  - {"smoke_rows": 3}
  - EXIT 0
- `frames --out $O/frames.json`:
  - {"ok": true, "attempts": 1, "chars": {"system": 576, "memory_header": 46, "line_prefix": 14, "current_label": 22}}
  - EXIT 0
- `write --facts $O/smoke_facts.jsonl --out $O/raw.jsonl --workers 1 --max-minutes 20`:
  - [mu407w] 3/3 written, 3 ok in this batch
  - {"rows": 3, "ok": 3, "errors": {}, "stopped": "done", "minutes": 0.9}
  - EXIT 0
  - raw lines after pilot-write: 3
- `pilot --frames $O/frames.json --raw $O/raw.jsonl`:
  - {"frames_ok": true, "smoke_rows": 3, "smoke_ok": 3, "scan_hits": {"usage limit": 0, "rate limit": 0, "error:": 0, "as an ai": 0, "openai": 0, "codex": 0, "i can't help with": 0}, "status": "PASS"}
  - PILOT_EXIT 0
  - verdict: pilot PASS (not FAIL/REVIEW), continued to steps 6-7

## 6. FULL WRITE (background)
- start: Sun Sep 27 05:59:06 UTC 2026, PID file 20339
- polls:
  - 05:59:10 alive, raw 3 lines
  - 06:05:57 alive, log [mu407w] 12/75 written, 12 ok in this batch; raw 15
  - 06:10:41 alive, log +[mu407w] 24/75 written, 12 ok in this batch; raw 27
  - 06:15:23 alive, log +[mu407w] 36/75 written, 12 ok in this batch; raw 39
  - 06:20:04 alive, log +[mu407w] 48/75 written, 12 ok in this batch; raw 51
  - 06:24:47 alive, log +[mu407w] 60/75 written, 12 ok in this batch; raw 63
  - 06:29:29 done (kill -0 failed: no such process)
- write.log full:
  - [mu407w] 12/75 written, 12 ok in this batch
  - [mu407w] 24/75 written, 12 ok in this batch
  - [mu407w] 36/75 written, 12 ok in this batch
  - [mu407w] 48/75 written, 12 ok in this batch
  - [mu407w] 60/75 written, 12 ok in this batch
  - [mu407w] 72/75 written, 12 ok in this batch
  - [mu407w] 75/75 written, 3 ok in this batch
  - {"rows": 78, "ok": 78, "errors": {}, "stopped": "done", "minutes": 29.3}
- last line of write.log: {"rows": 78, "ok": 78, "errors": {}, "stopped": "done", "minutes": 29.3}
- no kill needed (finished before 70-min limit)
- raw lines final: 78

## 7. SELECT AND CHECK
- `select --facts $O/facts_all.jsonl --raw $O/raw.jsonl --out-panel $O/panel/items.jsonl --out-facts $O/facts.jsonl`:
  - {"panel": 60, "smoke": 3}
  - SELECT_EXIT 0
- `python -B scripts/claude_mu405_check.py --panel $O/panel/items.jsonl --facts $O/facts.jsonl`:
  - {"chats": 63, "panel": 60, "smoke": 3, "session1_turns": 189, "session2_turns": 315, "problems": {}}
  - CHECK_EXIT 0
- `scan --frames $O/frames.json --raw $O/raw.jsonl`:
  - {"kept_chats": 78, "scan_hits": {"usage limit": 0, "rate limit": 0, "error:": 0, "as an ai": 0, "openai": 0, "codex": 0, "i can't help with": 0}, "repeated_messages": 26, "max_repeat": 12}
  - SCAN_EXIT 0

## 8. FILES COPIED
- artifacts/claude-mu407-20260927/prep/facts_all.jsonl (78 lines)
- artifacts/claude-mu407-20260927/prep/smoke_facts.jsonl (3 lines)
- artifacts/claude-mu407-20260927/prep/frames.json (5 lines)
- artifacts/claude-mu407-20260927/prep/raw.jsonl (78 lines)
- artifacts/claude-mu407-20260927/prep/write.log
- artifacts/claude-mu407-20260927/prep/panel/items.jsonl (63 lines)
- artifacts/claude-mu407-20260927/prep/facts.jsonl (63 lines)
- this RESULTS.md (counts only; no chat or frame text pasted)

writer: Luna (gpt-6-luna), helper sha256 342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e
