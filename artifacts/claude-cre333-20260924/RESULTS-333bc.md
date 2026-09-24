# rent-333bc-creative: REGISTERED runs of 333b and 333c — RAN, 1 rental

Task: handoff/queue/rent-333bc-creative.md. Marks: PASSMARKS-333b.md, PASSMARKS-333c.md
(read first, with VERIFY-333.md and PASSMARKS.md). Panel
artifacts/claude-creativepanel333-20260924 is TEST-ONLY: never opened, printed, or
quoted; run once via the month-end runners. No reader needed.

## Preconditions checked on the Mac (integer counts)

- `git fetch -q origin main builder-outbox`: ok (origin/main 52370485, origin/builder-outbox 4696b00a).
- DUPLICATE check: `git ls-tree -r origin/builder-outbox --name-only` lists
  `artifacts/claude-cre333-20260924/` with `run/` and `run-twinb/` only, no `run-b`:
  NOT a duplicate, proceed was correct.
- Credit at start: $5.31 (task BUDGET $1.00). No instance labelled
  `rent-333bc-creative` was live at start (5 unrelated instances live).
- Code tree built per the rent kit: `git archive origin/builder-outbox` +
  `git archive origin/main` (main on top) + `self122_head.pt` copied in, sha256
  `5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25` (match).
  Packed `/tmp/cre333bc_tree.tgz` (157 MB) and uploaded.

## Rental: 1 of 4 allowed, 1 usable

| # | Offer (RTX 5090) | dph ($/h) | Contract | Outcome |
|---|---|---|---|---|
| 1 | 48989513 (KR, 16 cores, 623 GB, 486/385 Mbps, rel 0.9942) | 0.5037 | 52457249 | `success: true`, running ~4 min after create, ssh + `nvidia-smi` ok, full run completed |

Offer search re-run immediately before create, per the task. Image
`pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, `--disk 80`,
`--label rent-333bc-creative`. Image torch 2.8.0+cu128 with CUDA True, no venv
needed. `pip install transformers safetensors huggingface_hub accelerate numpy`
(env only). BASE snapshot
`/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc`
commit `87179e5c1f455ef22e6223592d2d61351b525bfc` (matches the kit's expected
value). Smoke test `S.route122('what is your name?')` returned without raising.
Every step ran under setsid/nohup with a log file. Post-destroy
`vastai show instances` confirms 0 `rent-333bc-creative` instances live (other
tasks' instances untouched).

## Spend

- Rented 17:29:43Z, destroyed ~17:46:30Z 2026-09-24: ~0.28 h x $0.5037/h ≈ $0.14
  (budget $1.00; trip wire never reached).

## On the rental

- Panel seal: `sha256sum -c SEAL.sha256.txt` from inside the panel folder:
  items.jsonl OK, README.md OK, audit.jsonl OK (3/3), exit 0.
- `python -B scripts/claude_cre333b_test.py` printed
  "333b/c tests: 2/2 OK (own look-alikes routed: 333 13/20, 333c 0/20)".
- `artifacts/claude-cre333-20260924/SEAL-code-333bc.sha256.txt` written BEFORE
  running (6/6 scripts):
  - `933315752d4e91f9beed06cdafa0ff95d0df5896ec34b477d795548f2f0c9999  scripts/claude_cre333_agent.py`
  - `60e6612b70cf8b7888d1174ba2a5abf34b4aeeb5d9cc5201080a4949ae539f1e  scripts/claude_cre333_run.py`
  - `cb24f0ad51c0bb7a5b529738f68bc41908c2e8a9bd0e233efa8874f876d00133  scripts/claude_cre333b_agent.py`
  - `cc6f650c9d5a947f099a7727ed818027a260d139cad2177063325dbbe940f2ac  scripts/claude_cre333b_wrap.py`
  - `9a9e1cb61b663aa85595e24bb59fd8fb95e91810f67f2f45a1f138421eecd1d6  scripts/claude_e2e336_twin.py`
  - `51c03e2cf5f477ba520b1eea6d33d4d6a36097e42882b950ab3b803416f2621a  scripts/claude_e2e336_twinb.py`
- Step 2, each its own process with PANEL and D written in full; first printed
  lines (checked before proceeding):
  - b P: `cre333b: Gen333b (thinking off); twin b`, wall 57 s.
  - b T: `cre333b: Gen333b (thinking off); twin b`, wall 112 s.
  - c P: `cre333c: Gen333b (thinking off), is_creative333c; twin b`, wall 37 s.
  All three exit 0.
- Step 3: `cp` commands exactly as specified. arm_B sha256
  `ddc490cfba193c6e784fc2cebf629638be13494e6d4b703a4cb34bd61d19a161`
  before and after (run/arm_B.jsonl, run-b/arm_B.jsonl, run-c/arm_B.jsonl all
  match: unchanged). run-b/arm_T.jsonl and run-c/arm_T.jsonl
  (`b694b051cfe849ccde1d548f893640ca026483101339c7dbddad84758561c41c`)
  are twin b's T, copied into run-c per the task. Score steps exit 0, wall ~0 s each.
- Step 4 mechanical counts (rows whose reply contains "<think", no reply read or
  quoted): run-b/arm_P.jsonl 0, run-b/arm_T.jsonl 0, run-c/arm_P.jsonl 0
  (expected 0/0/0).
- All 13 files (6 run-b + 6 run-c + SEAL-code-333bc) copied back to the Mac
  BEFORE destroying; local sha256 matches remote sha256 for all 13.
  `judge_creative.jsonl` was never opened and no reply is quoted anywhere in
  this file. Month-end code untouched (no edits anywhere).

## Scorer printed summaries

run-b (333b):
`{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 17, "P_controls_routed": 13, "P_creative_routed": 25, "P_fallbacks": 0, "P_ms_creative_median": 959.7, "control_items": 30, "creative_items": 40}`

run-c (333c):
`{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 26, "P_controls_routed": 4, "P_creative_routed": 25, "P_fallbacks": 0, "P_ms_creative_median": 901.3, "control_items": 30, "creative_items": 40}`

## Marks judged now (P333.1, P333.2); the rest are judged later by the thread

| Mark | Bar | 333b (run-b) | 333c (run-c) |
|---|---|---|---|
| P333.1 notebook events on creative turns (P) | 0 | 0 PASS | 0 PASS |
| P333.2 controls where P's reply and stored triples equal B's | ≥ 29/30 | 17/30 FAIL | 26/30 FAIL |

Also observed (report-only, no bar applied here): 333b routed 13 controls and 25
creative turns with 0 fallbacks (median 959.7 ms/creative turn); 333c routed 4
controls and 25 creative turns with 0 fallbacks (median 901.3 ms/creative turn).
P333.3/P333.4/P333.5 need the blind judges (packets in each run's
`judge_creative.jsonl`, unopened) and are judged later by the thread.
