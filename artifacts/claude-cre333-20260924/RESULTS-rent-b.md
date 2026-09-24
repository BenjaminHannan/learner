# rent-333b-creative: REGISTERED run of exp 333 (creative v1) — RAN, 1 rental

Re-queue of rent-333-creative (HOST-FAIL, nothing run). Rental count starts fresh: 1 of 4 used.

## Preconditions checked on the Mac (integer counts)

- `git fetch -q origin main builder-outbox`: ok.
- DUPLICATE check: `git ls-tree -r origin/builder-outbox --name-only` lists
  `artifacts/claude-cre333-20260924/PASSMARKS.md`, `RESULTS-run.md`,
  `SEAL-code.sha256.txt` and no `run/` dir: NOT a duplicate, proceed was correct.
- Credit at start: $6.56 (task BUDGET $1.50). No instance labelled
  `rent-333b-creative` was live at start (3 unrelated instances live).
- Code tree built per the rent kit: `git archive origin/builder-outbox` +
  `git archive origin/main` (main on top) + `self122_head.pt` copied in, sha256
  `5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25` (match).
  Packed `/tmp/cre333b_tree.tgz` (164 MB) and uploaded.
- Panel: `artifacts/claude-creativepanel333-20260924/` present in the tree;
  items never opened, printed, or quoted.

## Rental: 1 of 4 allowed, 1 usable

| # | Offer (RTX 5090) | dph ($/h) | Contract | Outcome |
|---|---|---|---|---|
| 1 | 52190830 (KR, 16 cores, 588 GB, 439/436 Mbps, rel 0.9985) | 0.4690 | 52451674 | `success: true`, running ~2.5 min after create, ssh + `nvidia-smi` ok, full run completed |

Image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, `--disk 80`,
`--label rent-333b-creative`. Image torch 2.8.0+cu128 with CUDA True, no venv
needed. `pip install transformers safetensors huggingface_hub accelerate numpy`
(env only). BASE snapshot commit `87179e5c1f455ef22e6223592d2d61351b525bfc`
(matches the kit's expected value). Smoke test `S.route122('what is your
name?')` returned without raising. Post-destroy `vastai show instances`
confirms 0 `rent-333b-creative` instances live (other tasks' instances untouched).

## Spend

- Rented ~16:44Z, destroyed ~17:04Z 2026-09-24: ~0.34 h x $0.4690/h ≈ $0.16
  (budget $1.50; trip wire never reached).

## On the rental

- Panel seal: `sha256sum -c SEAL.sha256.txt` from inside the panel folder:
  items.jsonl OK, README.md OK, audit.jsonl OK (3/3), exit 0.
- `artifacts/claude-cre333-20260924/SEAL-code-rent.sha256.txt` written BEFORE
  running (4/4 scripts):
  - `933315752d4e91f9beed06cdafa0ff95d0df5896ec34b477d795548f2f0c9999  scripts/claude_cre333_agent.py`
  - `60e6612b70cf8b7888d1174ba2a5abf34b4aeeb5d9cc5201080a4949ae539f1e  scripts/claude_cre333_run.py`
  - `fe32149826bbd86651e4609bbf561af4215fe8b3100477f12ca4d28d5c9bdcb9  scripts/claude_e2e336_run.py`
  - `9a9e1cb61b663aa85595e24bb59fd8fb95e91810f67f2f45a1f138421eecd1d6  scripts/claude_e2e336_twin.py`
- Arms (each its own process, full commands as specified, all exit 0):
  - B: wall 5 s, `arm_B.jsonl` 70 rows (40 creative, 15 control_teach, 15 control_ask).
  - P (`--gen-model BASE`): wall 60 s, `arm_P.jsonl` 70 rows (same split).
  - T (`--gen-model BASE`): wall 311 s, `arm_T.jsonl` 70 rows (same split).
  - Score step: exit 0, wrote `summary.json`, `judge_creative.jsonl`, `judge_key.json`.
- All 7 files copied back to the Mac BEFORE destroying; local sha256 matches
  remote sha256 for all 7 (arm_B, arm_P, arm_T, judge_creative, judge_key,
  summary, SEAL-code-rent). `judge_creative.jsonl` was never opened and no
  reply is quoted anywhere in this file. Month-end code untouched (no edits
  anywhere).

## Scorer printed summary (`summary.json`)

{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 17, "P_controls_routed": 13, "P_creative_routed": 25, "P_fallbacks": 25, "P_ms_creative_median": 1172.3, "control_items": 30, "creative_items": 40}

## Marks judged now (P333.1, P333.2); the rest are judged later by the thread

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P333.1 notebook events on creative turns (P) | 0 | 0 | PASS |
| P333.2 controls where P's reply and stored triples equal B's | ≥ 29/30 | 17/30 | FAIL |

Also observed (report-only, no bar applied here): P routed 13 controls and 25
creative turns; P fallbacks 25; P median ms per creative turn 1172.3.
P333.3/P333.4/P333.5 need the blind judges (packets in `run/judge_creative.jsonl`,
unopened) and are judged later by the thread.
