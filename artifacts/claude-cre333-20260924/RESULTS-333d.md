# RESULTS-333d: registered run of 333d (rent-333d-creative, 2026-09-24)

Registered run of 333d per PASSMARKS-333d.md (marks fixed before the run; panel
artifacts/claude-creativepanel333-20260924 is TEST-ONLY and was never opened).
One process: `python -B scripts/claude_cre333d_wrap.py scripts/claude_cre333_run.py
--panel artifacts/claude-creativepanel333-20260924 --arm P
--gen-model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
--out artifacts/claude-cre333-20260924/run-d`.
Its first printed line was `cre333d: Gen333b (thinking off), install_creative333d
(338-style generation, 333c routing); twin b`.

Pre-flight on the rental: `sha256sum -c SEAL.sha256.txt` inside the panel folder:
all OK (items.jsonl, README.md, audit.jsonl OK).
`python -B scripts/claude_cre333d_test.py` printed `333d tests: 2/2 OK`.
SEAL-code-333d.sha256.txt (hashes of the six scripts) was written before running.

Step 3: `run/arm_B.jsonl` and `run-b/arm_T.jsonl` (from origin/builder-outbox)
copied into run-d/ unchanged: sha256 before, after copy, and after copy-back to
the Mac are identical (arm_B ddc490cfba193c6e784fc2cebf629638be13494e6d4b703a4cb34bd61d19a161;
arm_T b694b051cfe849ccde1d548f893640ca026483101339c7dbddad84758561c41c).
Then `python -B scripts/claude_cre333_run.py --panel ... --score .../run-d`.

## Printed summary (run-d/summary.json)

{"P333.1_creative_events_P": 0, "P333.2_controls_equal_B": 26, "P_controls_routed": 4, "P_creative_routed": 25, "P_fallbacks": 2, "P_ms_creative_median": 693.3, "control_items": 30, "creative_items": 40}

Counts: arm_P 70 rows, arm_B 70 rows, arm_T 70 rows.

## Marks (bars from PASSMARKS.md)

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P333.1 notebook events on creative turns (P) | 0 | 0 | PASS |
| P333.2 controls where P's reply and stored triples equal B's | >= 29/30 | 26/30 (4 controls routed) | FAIL |

Report only: 25/40 creative items routed, 2 fallbacks on creative turns,
P_ms_creative_median 693.3 ms. P333.3/P333.4/P333.5 need the blind judge and are
not run here; judge_creative.jsonl was written by the scorer and was not opened.

## Mechanical count (step 4)

Rows in run-d/arm_P.jsonl whose reply contains `<think`: 0 of 70 (expected 0).
No reply text was read or quoted.

## Run facts

- GPU: 1x NVIDIA GeForce RTX 5090 (vast.ai contract 52460993, label rent-333d-creative).
- Instance wall: 0.629 h at $0.4944/h = $0.311 (budget $0.60; under).
- Base model: openbmb/MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc (expected hash; matches).
- Wall time: P arm finished 2026-09-24 18:31 UTC; score finished 18:36 UTC.
- Environment deviations (reported, run unaffected): the image's torch 2.4.0 was
  too old for transformers 5.17.0 and lacked sm_120 kernels for the 5090, and its
  torchvision/torchaudio were stale; torch was upgraded to 2.8.0+cu128,
  torchvision to 0.23.0+cu128, torchaudio to 2.8.0. Month-end code was not edited.
