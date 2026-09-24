# RESULTS-333e: REGISTERED run of 333e (rent-333e-creative, 2026-09-24)

Registered run of 333e per artifacts/claude-cre333-20260924/PASSMARKS-333e.md
(marks fixed before the run; panel artifacts/claude-creativepanel333-20260924
is TEST-ONLY, 5th run, never opened, printed, or quoted).
Two arms, each one change, one process each via
scripts/claude_cre333e_wrap.py with CRE333E_ARM and CRE333E_HEAD.
Month-end code untouched (no edits anywhere).

## Preconditions on the Mac (integer counts)

- `git fetch -q origin main builder-outbox`: ok.
- DUPLICATE check: `git ls-tree origin/builder-outbox` lists
  artifacts/claude-cre333-20260924/run, run-b, run-c, run-d, run-twinb
  and no run-e1: NOT a duplicate, proceed was correct.
- Credit at start: $5.49 (task BUDGET $1.50). No instance labelled
  `rent-333e-creative` live at start (4 unrelated instances live).
- Code tree per rent kit: `git archive origin/builder-outbox` +
  `git archive origin/main` (main on top) + self122_head.pt copied in,
  sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25
  (match). Packed /tmp/cre333e_tree.tgz (157 MB), uploaded via scp.
- Panel present in tree (filenames only: README.md, SEAL.sha256.txt,
  audit.jsonl, items.jsonl); items never opened.

## Rental: 1 of 4 allowed, 1 usable

- Offer RTX 5090 (search `gpu_name=RTX_5090 reliability>=0.98 rentable=true`
  -o dph, re-run before create; CPU 16, disk 80, up 567 / down 584 Mbps,
  rel 0.9986, KR): dph $0.5037037/h, contract 52480261, label
  rent-333e-creative, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime,
  --disk 80, --ssh.
- Running ~3 min after create; ssh + nvidia-smi ok.
- Image torch 2.8.0+cu128 CUDA True, no venv needed.
  `pip install transformers safetensors huggingface_hub accelerate numpy`
  (env only). BASE snapshot
  /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
  (commit matches kit expected 87179e5c1f455ef22e6223592d2d61351b525bfc).
  Smoke `S.route122('what is your name?')` returned without raising.
- Post-destroy `vastai show instances` confirms 0 rent-333e-creative live.

## Spend

- Rented start 20:35:04Z, destroyed 20:47:22Z 2026-09-24: ~0.205 h x
  $0.5037037/h = ~$0.10 (budget $1.50; trip wire never reached).
- Credit $5.49 at start; auto-refill enabled.

## On the rental (full commands with full paths as specified)

- Panel seal from inside artifacts/claude-creativepanel333-20260924:
  `sha256sum -c SEAL.sha256.txt`: items.jsonl OK, README.md OK,
  audit.jsonl OK (3/3), exit 0.
- `python -B scripts/claude_cre333e_test.py` printed `333e tests: 2/2 OK`.
- `python -B scripts/claude_cre333d_test.py` printed `333d tests: 2/2 OK`.
- `artifacts/claude-cre333-20260924/SEAL-code-333e.sha256.txt` written
  BEFORE running (9 lines):
  - 933315752d4e91f9beed06cdafa0ff95d0df5896ec34b477d795548f2f0c9999  scripts/claude_cre333_agent.py
  - 60e6612b70cf8b7888d1174ba2a5abf34b4aeeb5d9cc5201080a4949ae539f1e  scripts/claude_cre333_run.py
  - cb24f0ad51c0bb7a5b529738f68bc41908c2e8a9bd0e233efa8874f876d00133  scripts/claude_cre333b_agent.py
  - 756c79e78460b44c244b9c83e803213c983853856447db0fef25d5bdc86e11f0  scripts/claude_cre333d_agent.py
  - 8093502755f910e35b77c9bb0ef6665aa803172f0921bf31baa8e02f96c873ca  scripts/claude_cre333e_agent.py
  - 4f97b107d111e9ac7f1be8d3377df671171c5de88c3d05b0e5b967a650f28f79  scripts/claude_cre333e_wrap.py
  - 26a2690a74c10797bbfd6244e4932042768864b0296ad2077ae75c18b5bb9815  scripts/claude_cre333e_train.py
  - 63f0e317423348007474946a54a4bab2c89d629c2458b498d33f3a3f743d5360  scripts/claude_chat338_agent.py
  - 3e0263cc9923161eec5fbdaeb20c543faff16a530e3df5d7a23ef299d9e8a91d  artifacts/claude-cre333e-20260924/head333e.json
- All steps ran under setsid/nohup with a log file (/root/run333e_full.log).

## Precheck (DEV only, never the panel)

Command:
`python -B scripts/claude_cre333e_train.py check --model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc --head artifacts/claude-cre333e-20260924/head333e.json --dev artifacts/claude-cre333e-dev-20260924 --bank artifacts/claude-e2e331-dev-20260924 --bank-lives 6,7,8,9,10`
Saved to artifacts/claude-cre333-20260924/PRECHECK-333e.json:

{
 "dev": {
  "creative": "39/40 called",
  "control_teach": "0/10 called",
  "control_ask": "2/20 called"
 },
 "bank": {
  "bank_teach": "1/29 called",
  "bank_smalltalk": "1/14 called",
  "bank_nosave": "0/8 called",
  "bank_correct": "0/5 called",
  "bank_ask": "0/35 called",
  "bank_creative": "4/5 called"
 }
}

Matches expected CPU counts exactly (dev creative 39/40, teach 0/10,
ask 2/20; bank other kinds 1+1+0+0+0 = 2/91, bank_creative 4/5).
Drift bars (dev creative <37/40 or controls teach+ask >3/30) not hit:
proceed was correct, no PRECHECK-DRIFT.

## Arms (each one process, full commands as specified, all exit 0)

- e1 first line:
  `cre333e: arm e1, head artifacts/claude-cre333e-20260924/head333e.json; Gen333b (thinking off), tool-call router, 333d writer (no chat); twin b`
  (starts with `cre333e: arm e1`: pass).
  Command: `CRE333E_ARM=e1 CRE333E_HEAD=artifacts/claude-cre333e-20260924/head333e.json python -B scripts/claude_cre333e_wrap.py scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --arm P --gen-model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc --out artifacts/claude-cre333-20260924/run-e1`
  Wall 20:42:55Z-20:43:58Z (~63 s). arm_P.jsonl 70 rows.
- e2 first line:
  `cre333e: arm e2, head artifacts/claude-cre333e-20260924/head333e.json; Gen333b (thinking off), tool-call router, writer sees the chat; twin b`
  (starts with `cre333e: arm e2`: pass).
  Command: `CRE333E_ARM=e2 CRE333E_HEAD=artifacts/claude-cre333e-20260924/head333e.json python -B scripts/claude_cre333e_wrap.py scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --arm P --gen-model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc --out artifacts/claude-cre333-20260924/run-e2`
  Wall 20:43:58Z-20:44:38Z (~40 s). arm_P.jsonl 70 rows.
- Score prep per arm: `artifacts/claude-cre333-20260924/run/arm_B.jsonl`
  (sha ddc490cfba193c6e784fc2cebf629638be13494e6d4b703a4cb34bd61d19a161)
  and `artifacts/claude-cre333-20260924/run-b/arm_T.jsonl`
  (sha b694b051cfe849ccde1d548f893640ca026483101339c7dbddad84758561c41c)
  from origin/builder-outbox copied into run-e1/ and run-e2/ unchanged
  (sha256 before, after copy identical, and after copy-back identical),
  then `python -B scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --score artifacts/claude-cre333-20260924/run-e1`
  and same for run-e2, both exit 0.
- arm_B/arm_P/arm_T row counts: 70/70/70 in run-e1, 70/70/70 in run-e2.

## Printed summaries (summary.json per arm)

run-e1:
{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 30, "P_controls_routed": 0, "P_creative_routed": 40, "P_fallbacks": 3, "P_ms_creative_median": 1063.0, "control_items": 30, "creative_items": 40}

run-e2:
{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 30, "P_controls_routed": 0, "P_creative_routed": 40, "P_fallbacks": 0, "P_ms_creative_median": 458.7, "control_items": 30, "creative_items": 40}

## Marks judged now (P333.1, P333.2 per arm; E.1, E.1b from run-e1)

| Mark | Bar | run-e1 | run-e2 | Verdict |
|---|---|---|---|---|
| P333.1 notebook events on creative turns (P) | 0 | 0 | 0 | PASS both |
| P333.2 controls where P reply and triples equal B | >= 29/30 | 30/30 | 30/30 | PASS both |
| E.1 routing (e1): creative items routed | >= 34/40 | 40/40 | - | PASS |
| E.1b routing (e1): control items routed | <= 2/30 | 0/30 | - | PASS |

Report only: e1 fallbacks 3, e2 fallbacks 0; routed e1 40 creative / 0 controls,
e2 40 creative / 0 controls; ms median creative e1 1063.0, e2 458.7.
P333.3/P333.4/P333.5 and E.2/E.2b need the blind judges (packets in
run-e1/judge_creative.jsonl and run-e2/judge_creative.jsonl, unopened) and are
judged later by the thread. judge_creative.jsonl was never opened and no reply
is quoted anywhere in this file.

## Mechanical count (step 6, never quote a reply)

Rows in run-e1/arm_P.jsonl whose reply contains `<think`: 0/70 (expected 0).
Rows in run-e2/arm_P.jsonl whose reply contains `<think`: 0/70 (expected 0).
No reply text was read or quoted.

## Run facts

- GPU: 1x NVIDIA GeForce RTX 5090 (vast.ai contract 52480261, label rent-333e-creative, KR, 16 cores).
- Instance wall: ~0.205 h at $0.5037037/h = ~$0.10 (budget $1.50; under).
- Base model: openbmb/MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc (matches).
- Wall time: e1 finished 2026-09-24 20:43:58 UTC; e2 + scores finished 20:44:38 UTC.
- All 14 files copied back to the Mac BEFORE destroying; local sha256 matches
  remote sha256 for all 14 (SEAL-code, PRECHECK, run-e1 x6, run-e2 x6).
  arm_B ddc490cf and arm_T b694b051 unchanged throughout.
- Environment deviations: none (image torch worked; no upgrades needed).
- Panel items never opened, printed, or quoted; judge_creative.jsonl never
  opened; no reply quoted. Month-end code untouched.
