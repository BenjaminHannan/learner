# rent-twinb RESULTS-twinb (twin-b re-runs of exps 338 and 333 arm T, 2026-09-24)

Re-run ONLY the plain-twin arm T of exps 338 and 333 with the fixed twin (twin b).
Why: artifacts/claude-chat338-20260924/VERIFY-338.md (old twin replies were unfinished "thinking").
Registrations: that file's "P338.4b" section and artifacts/claude-cre333-20260924/PASSMARKS-addendum-twinb.md.
Panels artifacts/claude-chatpanel338-20260924 and artifacts/claude-creativepanel333-20260924 are TEST-ONLY:
run once each, never read item by item, never quoted. No judge_*.jsonl opened. No reply quoted.

## Step 1 seals (rental /root/work/tree)
- Panel SEAL (`artifacts/claude-chatpanel338-20260924/SEAL.sha256.txt`, `sha256sum -c` from inside panel folder): all OK (items.jsonl OK, README.md OK).
- Panel SEAL (`artifacts/claude-creativepanel333-20260924/SEAL.sha256.txt`, `sha256sum -c` from inside panel folder): all OK (items.jsonl OK, README.md OK, audit.jsonl OK).
- `artifacts/claude-chat338-20260924/SEAL-code-twinb.sha256.txt` written BEFORE running (5 scripts, sha256sum):
  - 9a9e1cb61b663aa85595e24bb59fd8fb95e91810f67f2f45a1f138421eecd1d6  scripts/claude_e2e336_twin.py
  - 51c03e2cf5f477ba520b1eea6d33d4d6a36097e42882b950ab3b803416f2621a  scripts/claude_e2e336_twinb.py
  - a5b426df032ccb7335755c0eec89bc7a71ad1d2087c2d4948a3f7338de3cdcdb  scripts/claude_twinb_wrap.py
  - 4e056edfcdb50299f29d755141228fb3d031f6a09f8551148a490f9d97bede5e  scripts/claude_chat338_run.py
  - 60e6612b70cf8b7888d1174ba2a5abf34b4aeeb5d9cc5201080a4949ae539f1e  scripts/claude_cre333_run.py

## Step 2 twin-b arm T runs (each its own process, BASE as in the rent kit)
BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- `python -B scripts/claude_twinb_wrap.py scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --arm T --gen-model BASE --out artifacts/claude-chat338-20260924/run-twinb` — first printed line: `twinb: the plain twin is Twin336b (enable_thinking=False)` (as required). Output: run-twinb/arm_T.jsonl, 400 rows.
- `python -B scripts/claude_twinb_wrap.py scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --arm T --gen-model BASE --out artifacts/claude-cre333-20260924/run-twinb` — first printed line: `twinb: the plain twin is Twin336b (enable_thinking=False)` (as required). Output: run-twinb/arm_T.jsonl, 70 rows.
- No reader needed or used. Code unedited.

## Step 3 score 338 only
- `cp artifacts/claude-chat338-20260924/run/arm_P.jsonl artifacts/claude-chat338-20260924/run-twinb/` — registered P rows from origin/builder-outbox, unchanged; sha256 before, after, and Mac copy all 9ea6fee229bd28129a528a09d719b12ecf045b8c73414ddeafdf8868305549da.
- `python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --score artifacts/claude-chat338-20260924/run-twinb` — printed summary (from run-twinb/summary.json, counts only):
  - P: turns 400, gave_up_or_canned 3, events_on_non_teach 3, ask_known_right 3/15, ask_unknown_dont_know 8/10, distinct_replies 337, most_common_reply_count 26, ms_median 850.5, ms_p90 1217.8
  - T (twin b): turns 400, gave_up_or_canned 0, events_on_non_teach 0, ask_known_right 0/15, ask_unknown_dont_know 7/10, distinct_replies 348, most_common_reply_count 18, ms_median 590.2, ms_p90 1383.4
  - conversations 60
- P numbers match the registered run (same rows). T numbers are the new twin-b baseline; P338.4b judging (blind Opus judge on the new pair packets, bar P preferred or tied >= 30/60) is left to the thread. 333 not scored here (blind judge on P333.5b left to the thread).

## Step 4 mechanical check (counts only, never a quote)
- artifacts/claude-chat338-20260924/run-twinb/arm_T.jsonl: rows 400, replies containing `<think` 0, empty replies 0.
- artifacts/claude-cre333-20260924/run-twinb/arm_T.jsonl: rows 70, replies containing `<think` 0, empty replies 0.

## Compute
- GPU: NVIDIA GeForce RTX 5090, 1x, vast.ai contract 52452309 (offer 44173708, 16 vCPU, 80 GB disk, KR), image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, torch 2.8.0+cu128 CUDA True.
- Hours (running instance 16:52:02Z–17:11:08Z destroy): ~0.32 h; dph $0.50370370; dollars ~$0.16 (budget $1.50, well inside).
- Credit at start $6.49. One rental total (no HOST-FAIL, no re-rents).
- Model commit hash (BASE openbmb/MiniCPM5-1B): 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).
- Wall time per step (rental, UTC 2026-09-24): 338 arm T ~370 s (started ~17:00, finished 17:06:14), 333 arm T 114 s (17:06:57–17:08:51), 338 score ~0 s (17:09:38).
- run-twinb/ folders copied back before destroy; 0 rent-twinb instances live after.
