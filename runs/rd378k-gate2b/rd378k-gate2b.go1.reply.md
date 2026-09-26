Running your gated label check — fetching main and verifying seals.
Seals check out — now running the fixed labeller on the gate dialogs.
Labelling done — now copying the sealed outputs into the worktree.
Files staged — final verification before the verdict.
FAIL

COMMIT=5f938199bcc15f9f0740f26be4d52678635d8b06
DUPLICATE check: no gate2 on origin/main or origin/builder-outbox (both ls-tree empty). Not a duplicate.
GPU: no (Mac CPU only, OpenRouter GLM 5.3 Flash).
Scripts never edited; all runs from /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/rd378k-gate2b via `uv run --offline --no-project --python 3.12 python -B`. Key only in ~/.config/openrouter/key, never printed. No "sk-or" in any of the three gate2 files.

SEAL (from tmp extract of $COMMIT):
- SEAL-ADD-C: 2 OK
- SEAL-ADD-D: 2 OK
- SEAL: 15 OK + 1 FAILED on scripts/claude_lis300_train.py (the ONLY allowed FAILED line, replaced by SEAL-ADD-D hash). No SEAL-MISMATCH.

Step 3 selftest wall 0.094s:
rd378k teacher2 selftest 1/1 ok

Step 4 label wall 8:53.01 (533.01s), cost_usd 0.0324, 74 calls:
(39 per-dialog lines then JSON)
[rd378k-teacher2] ta-d01 ok
[rd378k-teacher2] ta-d05 ok
[rd378k-teacher2] ta-d12 ok
[rd378k-teacher2] ta-d13 ok
[rd378k-teacher2] ta-d15 ok
[rd378k-teacher2] ta-d17 ok
[rd378k-teacher2] ta-d20 ok
[rd378k-teacher2] tb-d01 ok
[rd378k-teacher2] tb-d02 unparsed
[rd378k-teacher2] tb-d04 ok
[rd378k-teacher2] tb-d05 ok
[rd378k-teacher2] tb-d08 unparsed
[rd378k-teacher2] tb-d10 ok
[rd378k-teacher2] tb-d17 ok
[rd378k-teacher2] tb-d18 ok
[rd378k-teacher2] tb-d20 unparsed
[rd378k-teacher2] tb-d21 ok
[rd378k-teacher2] tc-d01 ok
[rd378k-teacher2] tc-d03 ok
[rd378k-teacher2] tc-d05 ok
[rd378k-teacher2] tc-d06 ok
[rd378k-teacher2] tc-d07 ok
[rd378k-teacher2] tc-d11 ok
[rd378k-teacher2] tc-d16 ok
[rd378k-teacher2] tc-d17 ok
[rd378k-teacher2] tc-d21 unparsed
[rd378k-teacher2] tc-d23 ok
[rd378k-teacher2] td-d07 ok
[rd378k-teacher2] td-d09 ok
[rd378k-teacher2] td-d11 ok
[rd378k-teacher2] td-d14 ok
[rd378k-teacher2] td-d22 ok
[rd378k-teacher2] te-d01 ok
[rd378k-teacher2] te-d08 unparsed
[rd378k-teacher2] te-d09 ok
[rd378k-teacher2] te-d12 ok
[rd378k-teacher2] te-d14 unparsed
[rd378k-teacher2] te-d19 ok
[rd378k-teacher2] te-d22 ok
{"dialogs": 39, "labelled": 33, "unparsed": 6, "per_kind": {"chat": {"dialogs": 23, "unusable": 1}, "overheard": {"dialogs": 16, "unusable": 5}}, "calls": 74, "failed_calls": 27, "notes": 555, "ok": 296, "unsupported": 210, "bad_cite": 36, "bad_when": 2, "bad_form": 11, "cost_usd": 0.0324}

Step 5 agree wall 0.094s:
{"compared": 555, "teacher_ok": 296, "judges_ok": 254, "both_ok": 233, "agree": 471, "kappa": 0.699, "judges_unsupported_teacher_ok": 35, "judges_unsupported": 252, "passes_label_rule": false}

Integer counts:
- dialogs 39, labelled 33, unparsed 6
- chat dialogs 23, unusable 1, usable 22 (95.7%)
- overheard dialogs 16, unusable 5, usable 11 (68.8%)
- calls 74, failed_calls 27, notes(compared) 555
- verdicts: ok 296, unsupported 210, bad_cite 36, bad_when 2, bad_form 11
- agree 471/555 = 84.9% (<85%), kappa 0.699 (>=0.5)
- untrue-note rate 35/252 = 13.9% (<=15%)
- labels.jsonl 308 lines, failures.jsonl 27 lines, teacher-log.txt 42 lines

Gate rows (PASSMARKS-C): overall FAIL (84.9% < 85% bar, kappa passes); untrue-notes PASS (13.9% <= 15%); coverage chat PASS (22/23), overheard FAIL (11/16 < 90%).

Copied to worktree (additive only, files verified identical, no sk-or): artifacts/claude-rd378k-20260926/gate2/labels.jsonl, artifacts/claude-rd378k-20260926/gate2/failures.jsonl, artifacts/claude-rd378k-20260926/gate2/teacher-log.txt. PUSH: artifacts/claude-rd378k-20260926/gate2
