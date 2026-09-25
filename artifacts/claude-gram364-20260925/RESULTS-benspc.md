# gram-364 RESULTS-benspc (BensPC registered run, 2026-09-25)

Verdict: RUN COMPLETE within 1.5 h cap. One arm P364 on bank H. No file edited; nothing trained.
Counts, hashes, paths, timings only. No reply, turn, truth, question or answer text is quoted anywhere in this file.
check/*.jsonl files were never opened (names/sizes/hashes only).

Time: Mac start 2026-09-25T16:42:20Z. Cap 2026-09-25T18:12:20Z (1.5 h). Arm end ~2026-09-25T16:55:49Z.
Score/check ~2026-09-25T16:56:31-36Z. Copy-back verified 2026-09-25T16:56Z (Mac local time 12:56).
GPU work only on BensPC; no rentals.
DUPLICATE guard: PASS (origin/builder-outbox had no artifacts/claude-gram364-20260925/run and no
artifacts/claude-gram364-20260925/RESULTS-benspc.md before start; verified via git cat-file, both missing).

## Setup

- Tree: git archive origin/builder-outbox then git archive origin/main on top (main wins),
  plus self122_head.pt sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match),
  tar 161 MB (169129336 bytes on BensPC), extracted to NEW folder
  C:/Users/benja/lis301/work/gram364/tree (Test-Path False before extract; earlier trees untouched).
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe, version 3.10.9.
  Env every command: PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1.
- READER = C:/Users/benja/lis301/work/run/merged (model.safetensors exists; sha from prior runs
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890, not re-hashed to save time).
- BASE = C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (exists).
- W = `python -B scripts/claude_winnl2_wrap.py`. First printed line of every W command:
  winnl2: Windows text-mode writes use Linux line endings (newline=''). Never WINNL-FAIL.
- RUN = artifacts/claude-gram364-20260925/run inside tree; created; gram364_parts.jsonl Test-Path False before step 4.
- No downloads, no installs.

## 1. Seals (step 1, BensPC tree root)

- artifacts/claude-gram364-bankH-20260925/SEAL.sha256.txt (run from inside that folder): 4 lines, 4 OK, 0 FAIL.
  - turns.jsonl 80e7df0113c4529ba6651423c6a16f872c81314c0c765df178969923f071fef5 OK
  - truth.jsonl 04ee5f01804d5cfdb4a6a059eb9e9dfe88f392efb7db42c9755583dda19beaae OK
  - README.md a5919e97632b8bf04e5d2cf93f8f6ec164188a6bfaf47d9333ce2ae801a9e60f OK
  - check_bank.py 1f4c850eab9fa6284cfe3386babb2fc5be25e5500ad09f4db7ca6793f1f4951b OK
- artifacts/claude-gram364-20260925/SEAL-code.sha256.txt (from tree root): 9 lines, 9 OK, 0 FAIL.
  (hashes match origin/main listing; Get-FileHash case-insensitive match, all 9 OK.)
- No SEAL-MISMATCH.

## 2. Tests (step 2, BensPC tree root, plain python except W CHECK)

- `python -B scripts/claude_gram364_test.py` printed exactly: gram364 tests: 45/45 OK
- `python -B scripts/claude_gram360_test.py` printed exactly: gram360 tests: 16/16 OK
- `python -B scripts/claude_chat338b_test.py` printed exactly: 338b tests: 3/3 OK
- `python -B scripts/claude_cre333d_test.py` printed exactly: 333d tests: 2/2 OK
- `python -B scripts/claude_vary330c_test.py` printed exactly: vary330c tests: 2/2 OK
- W CHECK `python -B scripts/claude_winnl2_wrap.py scripts/claude_winnl2_test.py probe` printed first line
  winnl2: Windows text-mode writes use Linux line endings (newline='')
  then one JSON line with "ok": true and "crlf": 0 (python 3.10.9, fix none, text_ok true, metadata_ok true).
  Expected ok true + crlf 0: met. Not WINNL-FAIL.

## 3. Sleep base checkpoint (step 3, plain as listed)

- Command: `python -B scripts/fable_reasoner44.py --stage base --seed 4102 --out C:/Users/benja/lis301/work/gram364/r44c`. Exit 0.
- Printed JSON line:
  {"stage": "base", "seed": 4102, "seconds": 13.5, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- r44c contains base-seed4102.json 1251 bytes, base-seed4102.pt 2969 bytes.
- Copied to artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt in tree.
- .pt sha256: 4655b7610b50e91b57dbb6a780f1935dba8863e3810c4877408d901f1be5edb3, size 2969 bytes.
  (matches both BensPC source and tree copy.)

## 4. Arm P364 (step 4, through W, GRAM360_LOG set, launched once)

- Command:
  GRAM360_LOG=artifacts/claude-gram364-20260925/run/gram364_parts.jsonl
  python -B scripts/claude_winnl2_wrap.py scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py
  --bank artifacts/claude-gram364-bankH-20260925 --arm claude_e2e364:build_364 --name P364
  --model C:/Users/benja/lis301/work/run/merged
  --gen-model C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  --out artifacts/claude-gram364-20260925/run
- Start 2026-09-25T16:47:59.7105515Z. End ~2026-09-25T16:55:49.9644191Z (arm_P364.jsonl LastWriteTimeUtc;
  gram364_parts.jsonl 2026-09-25T16:55:49.9488127Z). Wall ~7 min 50 s. Exit inferred 0
  (wrote line present, 256 rows, no traceback, no python process after; see deviation note).
- First printed line: winnl2: Windows text-mode writes use Linux line endings (newline='')
- Second printed line: twinb: the plain twin is Twin336b (enable_thinking=False)
- Per-life lines: 10 lines [336/P364] e2e-g364-01..10 with turns 20,20,20,20,19,20,20,20,20,20 (sum 199).
- Last wrote line: wrote arm_P364.jsonl rows=256 lives=10
- run/ files: arm_P364.jsonl 142203 bytes 256 lines; gram364_parts.jsonl 92595 bytes 256 lines.
- Deviation: powershell $ErrorActionPreference='Stop' turned the transformers stderr warning
  (`[transformers] torch_dtype is deprecated! Use dtype instead!`) into a NativeCommandError after the
  wrote line, so arm_exit/arm_end echo lines were not printed in that ssh session. Exit 0 inferred from
  wrote line + complete files + no traceback. No relaunch (Run ONCE kept; process list shows no python after).

## 5. Scorer (step 5, through W)

- Command: python -B scripts/claude_winnl2_wrap.py scripts/claude_e2e336_score.py
  --bank artifacts/claude-gram364-bankH-20260925 --runs artifacts/claude-gram364-20260925/run/arm_P364.jsonl
  --out artifacts/claude-gram364-20260925/score
- Start 2026-09-25T16:56:31.6090783Z, end 2026-09-25T16:56:31.6896765Z. Exit 0.
- First printed line: winnl2 line above.
- Printed scorer line (counts only, no reply text):
  {"arm": "P364", "asks": {"ALL": {"ABSTAIN": 41, "CONFIRM_OTHER": 8, "RIGHT": 11, "RIGHT_CONFIRM": 4, "WRONG_CANDIDATE": 8}, "edit": {"ABSTAIN": 5, "CONFIRM_OTHER": 4, "WRONG_CANDIDATE": 1}, "never_told": {"RIGHT": 8, "WRONG_CANDIDATE": 2}, "one_hop": {"ABSTAIN": 8, "CONFIRM_OTHER": 1, "RIGHT": 2, "RIGHT_CONFIRM": 4, "WRONG_CANDIDATE": 2}, "partial": {"ABSTAIN": 3, "WRONG_CANDIDATE": 1}, "reversal": {"ABSTAIN": 9, "WRONG_CANDIDATE": 1}, "two_hop": {"ABSTAIN": 7, "CONFIRM_OTHER": 3, "RIGHT": 1}, "yesno": {"ABSTAIN": 9, "WRONG_CANDIDATE": 1}}, "clarify_replies": 14, "confirm_rows": 57, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 42, "day1_saved_facts_kept_at_end": 42, "distinct_replies": 138, "facts_saved": 54, "facts_total": 123, "most_common_reply_count": 9, "ms_median": 1991.9, "ms_p90": 3283.8, "new_triples": 62, "new_triples_owner_value_unsupported": 7, "nosave_turns_with_writes": 0, "user_rows": 199}
- score/ files (4): grammar_P364.jsonl 19847 bytes; judge_asks_P364.jsonl 1594 bytes;
  judge_saves_P364.jsonl 46077 bytes; mechanical.json 1155 bytes. judge_*.jsonl never opened.

## 6. Checker (step 6, through W)

- Command: python -B scripts/claude_winnl2_wrap.py scripts/claude_gram364_check.py
  --bank artifacts/claude-gram364-bankH-20260925 --run artifacts/claude-gram364-20260925/run/arm_P364.jsonl
  --log artifacts/claude-gram364-20260925/run/gram364_parts.jsonl --out artifacts/claude-gram364-20260925/check
- Start 2026-09-25T16:56:36.8180443Z, end 2026-09-25T16:56:36.9307997Z. Exit 0.
- First printed line: winnl2 line above.
- Last printed line (JSON summary, counts only; no separate WORDS/ASK lines printed by this checker version):
  {"P364.3": "FAIL", "P364.3_ask_class": 0, "P364.3_confirm_answer": 2, "P364.3_confirm_flag": 0, "P364.4": "PASS", "P364.4_word_losses": 0, "distinct_all_final": 191, "distinct_rule_final360": 146, "distinct_rule_final364": 146, "distinct_rule_raw": 146, "nonrule_changed": 0, "nonrule_parts": 111, "replies_changed": 43, "rows": 256, "rule_parts": 183, "rule_parts_changed": 48, "rule_parts_differ_from_360": 8}
- check/ files (5, never opened): all_final.jsonl 19656 bytes; check.json 430 bytes;
  rule_final360.jsonl 9621 bytes; rule_final364.jsonl 9745 bytes; rule_raw.jsonl 9611 bytes.

## 7. CRLF counts + copy-back (step 7)

- Byte counts of "\r\n" (expected 0, all 0), BensPC and Mac identical:
  run/arm_P364.jsonl bytes=142203 crlf=0
  run/gram364_parts.jsonl bytes=92595 crlf=0
  score/grammar_P364.jsonl bytes=19847 crlf=0
  score/judge_asks_P364.jsonl bytes=1594 crlf=0
  score/judge_saves_P364.jsonl bytes=46077 crlf=0
  score/mechanical.json bytes=1155 crlf=0
  check/all_final.jsonl bytes=19656 crlf=0
  check/check.json bytes=430 crlf=0
  check/rule_final360.jsonl bytes=9621 crlf=0
  check/rule_final364.jsonl bytes=9745 crlf=0
  check/rule_raw.jsonl bytes=9611 crlf=0
  Total files: 11. Total CRLF: 0.
- Copy-back: scp 11 files BensPC tree -> Mac worktree artifacts/claude-gram364-20260925/run,score,check.
  Sizes match BensPC (listed above). Sha256 match BensPC (case-insensitive):
  run/arm_P364.jsonl fd2f57e2bc831e759ab3848c98a783210ab657ed059b24d1b94cd1f1ef9f82aa
  run/gram364_parts.jsonl 2ea7d82a94fabf50139aaa4bd31b929baadc91f0e65e75cc2b24f246dace4ce1
  score/grammar_P364.jsonl f04fefa926b2046290be39747ed047c74a0a95da6ecaf3e1694d9bc77039cfb5
  score/judge_asks_P364.jsonl f5470551b8a2583250a22868b220f957bf8d77dfa110be36ce24fcad29266d47
  score/judge_saves_P364.jsonl f4070d1aa372f9e06ec6ce4c29a25eda76c744321b0841413a828149a9d12bbc
  score/mechanical.json ea351c143c0d0373259f592e9c427eb799d794c1a949908e481411350cba2bce
  check/all_final.jsonl 9faff14424554dbcba6b764133490c57390780b0744e032400f2d28aee729822
  check/check.json 219b2583401ccb8be04a9c56fc4c044eb9f0aa130da0f61c90b7c98e4775f282
  check/rule_final360.jsonl 7cc0d5146ff7c5a44e9a062ae45fb84ff7001b629b944be02124e48d9a742dde
  check/rule_final364.jsonl b8533f7468931d9c61a480189f6aab526c042eb444fce50d21fecc32ae6bc55c
  check/rule_raw.jsonl 759e62311fc91ac64883fd7f3d9015510d7b594F34b10dd9e81688bc1ceceb76
- Models left on BensPC. Tree, r44c, tgz left on BensPC. Nothing deleted.

## GPU

- NVIDIA GeForce RTX 5070 Ti, 16303 MiB total, driver 591.86, CUDA 13.1.
- Before arm: 15540 MiB free, no python.exe processes (desktop processes only). One GPU job at a time kept.
- After arm: no python processes. Disk C free 35.86 GB before.

## Tracebacks

- None. All exits 0 (arm exit inferred 0, see deviation). One stderr warning only:
  `[transformers] torch_dtype is deprecated! Use dtype instead!` (after wrote line, not a traceback).
- No SLEEP-NOT-LEARNING, no STATE-RESET-FAILED, no SEAL-MISMATCH, no WINNL-FAIL, no SMOKE-FAIL.
- Checker reports P364.3 FAIL (confirm_answer 2) and P364.4 PASS (word_losses 0) as counts above; grading of
  P364.1/P364.2 is not in this run (grade prep is separate).

## PUSH

- artifacts/claude-gram364-20260925/RESULTS-benspc.md (this file, NEW)
- artifacts/claude-gram364-20260925/run (2 files above)
- artifacts/claude-gram364-20260925/score (4 files above)
- artifacts/claude-gram364-20260925/check (5 files above)
