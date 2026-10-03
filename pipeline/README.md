# pipeline/ — the real Premonition training/eval/scoring code

Exported 2026-10-03 from the repo's `scripts/` + `scripts/cap256_launch/`. The 67 English-pilot files were
compared byte-for-byte (SHA-256) with the copies that actually ran on BensPC (package
`launch-cap256/pkg/english-pilot-v1-20261003T142114Z`): all identical, except `sweep_english_trainfit_v1.py`
(this copy is newer: it adds the `--aux-weight` / overfit options). Nothing here was run on Linux.

**Not included (on purpose):** checkpoints, model weights, feature caches, anything gold/blind/reserved
(fresh eval items, fresh inputs, `FRESH-EVAL-*`, eval gold). `english_blind_paraphrase_sheet_v1.py` is just code
(it reads gold at run time from a path you supply).

## Layout
- `scripts/` — model code (`sol_*`, `claude_*`, `fable_*`: spatial core, translator/decoder, calculator tools, reasoner).
- `scripts/cap256_launch/` — pilot trainer, eval generator, scorer, runtime helpers, calculator drivers, tests.
- `configs/english-pilot-v1/` — `TRAIN-CONFIG-v2.json`, `EVAL-CONFIG-v1.json`, `PROBE-CONFIG-v1.json`.
- `artifacts/...` — the small pinned train-side data, at the exact relative paths the configs name
  (bank, frames, schedule, provenance). Run everything with `pipeline/` as the root.

## Entry points (English paraphrase pilot)
| step | file |
|---|---|
| train (4 runs: seed 0/1 x control/treatment) | `scripts/cap256_launch/train_english_paraphrase_pilot_windows_v1.py` |
| generate fresh-eval + TRAIN-panel answers (sealed) | `scripts/cap256_launch/eval_english_fresh_windows_v1.py` |
| score (verifies seal, then reads gold) | `scripts/cap256_launch/score_english_free_answer_v1.py` |
| train-fit-only sweep (lr / updates / warmup / overfit / aux loss) | `scripts/cap256_launch/sweep_english_trainfit_v1.py` |
| zero-update probe | `scripts/cap256_launch/english_zero_update_probe_v1.py` |
| Windows driver (job-object caps, GPU-BUSY marker) | `scripts/cap256_launch/execute_english_paraphrase_pilot_windows_v1.py` |
| 9216-update eval/score wrappers | `eval_english_9216_v1.py`, `score_english_9216_v1.py` |
| tests | `test_english_pilot_stdlib_v1.py` (no torch), `test_english_pilot_torch_v1.py` |

Calculator / reasoner: `calculator_pc_driver.py`, `calculator_eval_resume_pc_driver.py`,
`calculator_recovery_pc_driver.py`, `calculator_runtime.py`, `calculator_tools.py`,
`audit_native_calculator_results.py`, `fresh_core_calculator_constructor.py`, `calculator_runtime_depth_compare.py`.
Configs/data exported (all under `pipeline/artifacts/cap256-launch/calculator-poc-v1/`): `RELEASE-MANIFEST-v3.json`
(the training config, sha256 40b2ef6e…), TRAIN frames, fixed schedules, token qualification, architecture contract,
throughput receipt, evaluation protocol, `BASELINE-FRESH-CONFIG.json`. Also added: `train_calculator_poc_v3.py`,
`eval_calculator_poc.py`, `train_primitive_curriculum_v2.py`. **Not exported:** the fresh/eval frames
(`EVAL-FRAMES-PRIVATE*.json`), and the source checkpoints the manifest pins (`run-capability256-continuation40-v1`
seed0/1 `final-resume.pt`, sizes not measured). The manifest's `storage_snapshot` path points into a `launch-cap256/pkg/`
folder that is not exported (the Mac copy is `scripts/cap256_launch/storage_snapshot.py`). Not run or tested here.

## Data a cloud box needs (not in the repo)
| file (path relative to root) | size | note |
|---|---|---|
| `artifacts/train-contextual-lr-stability-v1/control/seed{0,1}/contextual/final-resume.pt` | 60.7 MB each | the two parent checkpoints; sha256 49a35023…, 4c3c410f… |
| `artifacts/sol-translator-20260929/ground-answer-v11-s0-loop/bootstrap-English-s0.pt` | 0.31 MB | decoder adapter; sha256 e8092da2… |
| LiquidAI/LFM2.5-1.2B-Instruct HF snapshot `0f604ada3f766f9f257460c4c9f0b5d6f69d431b` | ~2.4 GB (estimate, not measured) | frozen LM; set `lm.model_path` in the config |
| `artifacts/english-pilot-v1/feature-cache/` | ~91 MB | rebuilt automatically on first run |
Outputs: each run writes a ~61 MB `final-checkpoint.pt` (+ 61 MB resume file while running). Ask Ben for the three
`.pt` files (they are not in git). The LM snapshot can be downloaded from Hugging Face at that revision.

## Run one training job on a fresh Linux GPU box (UNTESTED on Linux)
```bash
cd pipeline
pip install torch transformers   # BensPC used Python 3.10; transformers needs huggingface-hub <1.0
export PYTHONPATH=.:scripts:scripts/cap256_launch HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# 1. put the three .pt files at the paths above; download the LM snapshot
# 2. copy configs/english-pilot-v1/TRAIN-CONFIG-v2.json to a new file, change:
#      "lm.model_path"        -> your local snapshot dir
#      "output_namespace"     -> a NEW relative dir (it must not exist)
#    (changing the config changes its sha256; pass the new one)
SHA=$(sha256sum my-train-config.json | cut -d' ' -f1)
printf 'BEGIN ENGLISH PARAPHRASE PILOT\n' | python scripts/cap256_launch/train_english_paraphrase_pilot_windows_v1.py \
    --root . --config my-train-config.json --config-sha256 $SHA --require-owned-stdin
```
That trains all four runs (2304 updates each, ~4.5 min/run on an RTX 5070 Ti). Notes:
- The worker needs `--require-owned-stdin` and the exact go-line on stdin, and `"dispatch_allowed": true` in the config.
- `resume_every_updates` must be one of 72/144/288/576. Update count is pinned to 2304 by the schedule; to train
  longer use `sweep_english_trainfit_v1.py --passes N` (it patches the pins; 4x = `--passes 128` fixed the underfit).
- Windows-specific parts (job-object caps in the driver, `ctypes` use in `sol_cloud_capability256_v1.py`, the
  CUDA allocator cap) have not been tried on Linux and may need small changes; skip the `execute_*` driver and call
  the worker directly as above.
- Budget fields in the config are fixed by `validate_budget`: 10 GiB CUDA cap, 0.00 spend cap.

## Status of results (see docs/premonition-status/LIVE.md on the other branch)
English pilot v1 at 2304 updates: UNDERFIT-VOID. At 9216 updates train fit 40–43/48, but fresh understanding 2–7/48,
transfer 1–3/48, no treatment effect: NULL (exploratory, eval v3 had been seen once).
