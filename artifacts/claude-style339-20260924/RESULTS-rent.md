# rent-339-style RESULTS-rent (REGISTERED exp 339, rented Linux GPU, 2026-09-24)

Registered run of exp 339 (learns how the user likes to be talked to), which e2e-339-style could not run on Windows.
Panel artifacts/claude-stylepanel339-20260924 is TEST-ONLY: never opened item-by-item, never quoted. No judge_*.jsonl opened. No panel reply quoted.

## Step 1 (seals, on rental, before running)
- Panel SEAL (`sha256sum -c SEAL.sha256.txt` from inside `artifacts/claude-stylepanel339-20260924`): 4/4 OK (turns.jsonl OK, truth.jsonl OK, lives.jsonl OK, README.md OK).
- SEAL-code-rent (`artifacts/claude-style339-20260924/SEAL-code-rent.sha256.txt`): 11/11 hashed BEFORE running, exact 11 prescribed paths.
- Deviation: SEAL-code-rent differs from builder `SEAL-code.sha256.txt` on 2/11 scripts (main evolved since the BensPC attempt): `scripts/claude_chat338_run.py` rent 4e056edfcdb50299f29d755141228fb3d031f6a09f8551148a490f9d97bede5e vs builder 65db231772dec0fea6b2a9d6a4c781a840f02d34e8755514943a4481edba4a53; `scripts/claude_e2e336_run.py` rent fe32149826bbd86651e4609bbf561af4215fe8b3100477f12ca4d28d5c9bdcb9 vs builder f797dfbcac23828b09bda43c2996140d92854a8ab61c5b8bed7c5c266eec6749. Other 9/11 identical. Tree = builder-outbox + main (main wins) per rent kit. Month-end code never edited.
- `self122_head.pt` sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 (match). READER `model.safetensors` sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match). `route122('what is your name?')` did not raise.
- BASE `openbmb/MiniCPM5-1B` snapshot commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).

## Step 2 (panel, 336 harness, each its own process)
Commands (PANEL = artifacts/claude-stylepanel339-20260924, OUT = artifacts/claude-style339-20260924/run, READER = /root/work/reader, BASE = openbmb/MiniCPM5-1B, HF_HUB_OFFLINE=1):
- `python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_chat338_run:build_P --name B --model READER --gen-model BASE`
- `python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_style339_run:build_P --name P --model READER --gen-model BASE`
- `python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm twin --name T --model BASE`
- `python -B scripts/claude_style339_run.py --panel PANEL --score OUT`

Rows written: arm_B.jsonl 854 rows / 60 lives; arm_P.jsonl 852 rows / 60 lives; arm_T.jsonl 768 rows / 60 lives.
Scorer printed summary (summary.json):
- P339.1_feedback_lives_saved_exactly_right: 17; feedback_lives 40; feedback_lives_with_nothing_saved 23; feedback_lives_with_extra_or_wrong 0.
- P339.2_control_lives_with_any_saved: 2; control_lives 20.
- lives 60. saved_by_label: casual 2, formal 5, longer 1, name 0, no_emoji 4, no_nickname 3, no_questions 2, shorter 2.

Marks:
- P339.1 (bar >= 32/40 exactly-right feedback lives): 17/40 FAIL.
- P339.2 (bar 0/20 control lives with any save): 2/20 FAIL (also above the proved-wrong threshold >1).
- P339.3 (day-3 blind-judge follow rate) is judged later by the month-end thread; judges not run here; judge_*.jsonl never opened.

## Step 3 (P339.4, readable DEV bank)
- `python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-style339-20260924/dev --arm claude_style339_run:build_P --name P339 --model READER --gen-model BASE`
- dev/arm_P339.jsonl: 248 rows / 10 lives.
- Rows whose reply starts with one of the ACK339 acknowledgements in scripts/claude_style339_agent.py: 0.
- P339.4 (bar 0 preferences saved on the 194-turn DEV bank): 0 PASS (count 0).

## Cost / machine / wall time
- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. Instance 52415511, offer 44173867, 16 vCPU, 70 GB disk, label rent-339-style, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, torch 2.8.0+cu128 True.
- Rate: $0.4991/h. Age at copy-back ~1.46 h (uptime ~85.5 min) = ~$0.73. Budget $3.50 respected. Credit at start $9.97.
- Model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc.
- Wall time per arm (UTC 2026-09-24): B ~13:07-13:22 (~15 min, 854 rows); P 13:23:43-13:38:24 (881 s, 14.7 min, 852 rows); T 13:39:48-13:57:36 (1068 s, 17.8 min, 768 rows); scorer 13:59:46 (<10 s); dev P339 14:00:12-14:03:24 (192 s, 3.2 min, 248 rows). No 10-min watchdog trigger; 1 rental total (within 4-rental cap); running job never stalled.
- run/ + dev/ rsync'd back to the Mac and row-count checked before destroy (B 854, P 852, T 768, dev 248 match). No other model downloaded. Code unedited throughout.
