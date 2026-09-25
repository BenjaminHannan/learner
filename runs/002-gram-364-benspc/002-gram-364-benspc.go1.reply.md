Registered GPU run — checking guards and assembling the sealed tree.
Duplicate check is clear — now verifying marks and setup docs.
Found the task spec — now mapping the remote execution path.
SSH is live — now auditing GPU state and prior trees.
Preflight passed — now building the sealed code tree.
Tree is staged on BensPC — now running seal checks and unit tests.
Bank seal verified — now checking code seals and test suites.
Checkpoint complete — launching the registered P364 arm on the GPU.
Arm finished clean — now scoring and checking the run.
All files verified — now drafting the counts-only results file.
Results file drafted — final verification before handoff.
Verdict: RUN COMPLETE. gram-364-benspc registered run P364 finished on BensPC inside 1.5 h cap, all steps 1-8 done, 11 files copied back with matching sizes/sha256 and 0 CRLF.

Marks table (integer counts, from checker/scorer output, no reply text):
| Mark | Result | Counts |
|---|---|---|
| Seals | PASS | bank H 4/4 OK; code 9/9 OK |
| Tests | PASS | 45/45, 16/16, 3/3, 2/2, 2/2; W CHECK ok true crlf 0 |
| Sleep base | OK | exit 0, seconds 13.5, .pt 2969 bytes, sha 4655b761… |
| Arm P364 | WROTE | rows 256, lives 10, turns sum 199; run files 2 |
| Scorer | OK | exit 0, user_rows 199, facts_total 123, distinct_replies 138, confirm_rows 57 |
| P364.3 | FAIL (counts) | ask_class 0, confirm_answer 2, confirm_flag 0 |
| P364.4 | PASS | word_losses 0 |
| Changed parts | counts | rule_parts 183, changed 48, differ_from_360 8, replies_changed 43, nonrule_changed 0 |
| CRLF | 0 | 11 files, all crlf 0 |
| Tracebacks | 0 | none; 1 stderr warning only |

Every move:
- DUPLICATE guard PASS (no run/, no RESULTS-benspc.md on origin/builder-outbox).
- Built tree via git archive builder-outbox then main + self122_head.pt 5ca02173… match, 161 MB tgz, NEW folder C:/Users/benja/lis301/work/gram364/tree (was absent).
- Seals/tests/W CHECK all met (lines above).
- Step 3 JSON + sha reported above.
- Arm start 2026-09-25T16:47:59Z, end ~16:55:49Z, first two lines winnl2 + twinb Twin336b, last line wrote arm_P364.jsonl rows=256 lives=10, exit inferred 0.
- Score start/end 16:56:31Z exit 0, checker 16:56:36Z exit 0, lines in RESULTS-benspc.md.
- Copy-back 11 files verified size+sha match.
- Wrote NEW artifacts/claude-gram364-20260925/RESULTS-benspc.md + run/ score/ check/ (additive only, no edits).

Misses/deviations (2):
1. Arm ssh session did not print arm_exit/arm_end because powershell ErrorActionPreference=Stop turned a transformers stderr warning into NativeCommandError after the wrote line. Exit 0 inferred from wrote line + 256-row files + no traceback + no process left. Run ONCE kept, no relaunch.
2. Checker printed a single JSON summary line; no separate WORDS/ASK lines in this version. Reported as counts only. check/*.jsonl never opened.

Common-rules report: additive only (new files only, no edits/deletes of existing files); fictional names (no person names in outputs, no reply/turn text quoted); TEST-ONLY panels never read item-by-item (bank H turns/truth/judge files never opened/printed/quoted; byte counts only); final reply is this report.

What it means in plain high-school English: the computer ran the new grammar fixer once on 10 fresh made-up lives and saved all its answers. The files all arrived safely with correct fingerprints and clean line endings. The automatic check says the fixer changed 48 word-parts, changed 43 replies, kept all slot words (0 lost), but flagged 2 confirm-answer differences (P364.3 FAIL). Whether the English actually got better is decided later by human graders, not by this run.

PUSH: artifacts/claude-gram364-20260925/RESULTS-benspc.md artifacts/claude-gram364-20260925/run artifacts/claude-gram364-20260925/score artifacts/claude-gram364-20260925/check
