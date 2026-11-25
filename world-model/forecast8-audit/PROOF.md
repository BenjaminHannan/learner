# Determinism audit proof

Working directory for every command below:

`<project>/PROBLEM-7/forecast8-audit`

## Scope and source fact

The pilot computes wall numbers from the in-memory float64 `preds_by_k[1]` inside `evaluate_model`, before `np.savez` casts `pred_k1` to float16 (`../forecast8-pilot2/train_v7.py:1047`, `../forecast8-pilot2/train_v7.py:1061`). No saved file contains those exact float64 wall inputs.

`audit.py` therefore:

- Stage 1 replays `score_block_open` on the saved float16 artifact and reports any difference from the saved wall numbers.
- Stage 2 regenerates float64 k1 predictions, compares their wall calls to the saved score, and separately checks exact equality after casting the regenerated array to float16.

No real audit stage was run on this Mac. There are no pilot runs here, the pinned pilot virtual environment is absent, and the available system Python has neither NumPy nor PyTorch. No real-stage results are claimed or fabricated. `audit.json` is written by `audit.py` when a real stage is run on the pilot Mac.

## Commands run on this Mac

| Command | Exit code | Result |
|---|---:|---|
| `python3 --version && python3 -c "import numpy, torch; print('numpy', numpy.__version__); print('torch', torch.__version__); print('mps', torch.backends.mps.is_available())"` | 1 | Python 3.14.6; stopped at `ModuleNotFoundError: No module named 'numpy'`. Numerical CPU replay cannot run locally. |
| `python3 -c "import ast, pathlib; p=pathlib.Path('audit.py'); ast.parse(p.read_text(), filename=str(p)); print('AST PASS')"` | 0 | `AST PASS` |
| `python3 -B audit.py --help` | 0 | Printed the expected `--root`, `--device`, `--stages`, and `--self-test` interface. |
| `python3 -B audit.py --self-test` | 0 | `SELFTEST PASS: stdlib audit helper plumbing` |
| `python3 -B -c "import audit; audit.preflight_path('/tmp/sealed_test.npz')"` | 1 | Expected refusal: `REFUSED: sealed path is forbidden: /tmp/sealed_test.npz`. The path was not opened. |
| `python3 -B -c "import audit; assert audit.parse_stages('train,score') == ('score','train'); print('STAGE PARSER PASS')"` | 0 | `STAGE PARSER PASS` |
| `command -v ruff mypy pyright || true` | 0 | No output; no lint or typecheck executable is installed. |

An initial `--self-test` run exited 1 because its synthetic fixture paired a `0.25` false-open rate with only two blocked samples, which cannot represent an integer confusion count. The fixture was corrected to `0.5`; the final self-test exits 0.

The self-test is stdlib-only. It exercises call bitmap round-tripping, first-difference detection, saved confusion-count recovery, and training first-difference reporting. It does not claim to test PyTorch or NumPy numerics.

## Script hash

Command: `shasum -a 256 audit.py`

```text
7df90ccd930083405aaba0d0619e24d77facbe3c83cdbca83164588c1744f2eb  audit.py
```

## Commands to run on the pilot Mac (not run here)

Run from this folder with the pinned pilot interpreter:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u audit.py --root ../forecast8-pilot2 --device mps
```

Subsets:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u audit.py --root ../forecast8-pilot2 --stages score
~/learner-ops/m3-torch/.venv/bin/python -B -u audit.py --root ../forecast8-pilot2 --stages model --device mps
~/learner-ops/m3-torch/.venv/bin/python -B -u audit.py --root ../forecast8-pilot2 --stages train --device cpu
```

MPS runs enforce the existing AC-power or battery-at-least-35-percent guard. The parent process uses a 570-second internal deadline, leaving margin under the requested 10-minute wall-time limit, and writes `audit.json` beside `audit.py`.

## Lead: real runs on the M3 (2026-11-25 17:07–17:12 ET; MPS lock held for each MPS run; battery 92%)
- Run 1 (MPS): score + model stages crashed, because load_score unpacked 2 values as 3. TRAIN DIFF at step 1, gradient_vector_sha256. Saved as audit_run1_mps.json.
- Lead fix: load_score returns (path, sha, value), and the canonical score read in worker_score was fixed the same way. Both are 2-line fixes.
- Run 2 (MPS): MODEL PASS for s7_uniform and s8_uniform. Two fresh replays, the saved predictions and the saved wall numbers all agree. TRAIN DIFF again at step 1, gradient_vector_sha256: the indices, batch tensors and loss match, but the gradients differ. Saved as audit_run2_mps.json.
- CPU train stage: PASS, two 20-step seed-7 replays bit-identical. Saved as audit_train_cpu.json.
- CPU score stage: PASS, two fresh score replays agree with the saved wall numbers. Saved as audit_score_cpu.json.
