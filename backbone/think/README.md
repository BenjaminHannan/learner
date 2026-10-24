# Think-1: how to run it

A small trained "thinking block" (16 slots, a 2.6M-parameter refiner, zero-start gates) on a frozen Qwen3.5-0.8B + arm A's LoRA, against
plain LoRA (a, aplus) and the looped-layers arm (b, bplus). Marks are fixed in `PREREG.md`; design in `DESIGN.md`; code contract in
`IMPL-SPEC.md`. Village model only; the `test` split is never built or read. Every arm runs through ONE harness, `think1.py`.

## Ben's PC (RTX 5070 Ti 16 GB), one line, from the repo root
```
THINK_JOBS=a:0,b:0,aplus:0,t:0,t1:0 bash backbone/think/run_box.sh
```
Needs Python with CUDA torch and `pip install -r backbone/requirements.txt` (transformers 5.20.2, peft 0.21.2; `flash-linear-attention`
makes the Gated DeltaNet layers fast). The first run builds the village data into `out/data` (about 12 min on 4 cores). Then add the rest
of seed 0 (`bplus:0` and the diagnostic `tw:0`), look at `out/think/SUMMARY.txt`, and run seeds 1 and 2 only if the futility rules there
do not fire. Re-running the same line skips every job whose result file exists.

Jobs are `ARM:SEED`, comma separated, run in the order given. Dependencies are automatic: `aplus`, `t`, `t1`, `tw` need
`out/think/a_s{S}/adapter`, `bplus` needs `out/think/b_s{S}/adapter`; if it is missing, that stage-1 arm runs first in the same box (a
result file whose adapter is gone is deleted and retrained, so the two always match).

| arm | what | steps (built into think1.py) | est. per seed on a 3090 (PREREG, suggested) |
|---|---|---|---|
| a | LoRA r16 on all layers | 418 | 1.3 h |
| b | a + layers 8-11 run 3x | 418 | 1.6 h |
| aplus | a's adapter, LoRA trained on | 1,254 more | 1.5 h |
| bplus | b's adapter, LoRA trained on | 1,254 more | seed 0 only |
| t | a's adapter frozen, board trains, L_max 8 (p 0.8) or 12 | 1,254 | 2.5 h |
| t1 | as t, L_max = 1 | 1,254 | 1.5 h |
| tw | as t1, 144 slots | 1,254 | seed 0 only, PC run |

Stage-2 arms draw rows from `random.Random(seed + 1000)` (same order for all five); stage 1 draws exactly as `backbone/train.py` does
(`random.Random(seed)`, pop from the end). No `--steps` in a prereg run.

## Vast (seed-0 screen only, cap $2.50, RTX 3090/4090)
```
python3 backbone/vast.py pack --out /tmp/think0 --label claude-think1-<branch> --hours 8 --env "THINK_JOBS=a:0,b:0,aplus:0,t:0,t1:0"
python3 backbone/vast.py search --max-dph 0.5            # pick an offer
python3 backbone/vast.py create --offer ID --args /tmp/think0/args.json --label claude-think1-<branch> --hours 8
python3 backbone/vast.py status | logs ID | cat ID /job/tree/out/think/SUMMARY.txt
```
`backbone/run_box.sh` installs the dependencies, then hands over to `backbone/think/run_box.sh` when `THINK_JOBS` is set. Extra
`think1.py` flags go in `THINK_FLAGS` joined with `+` (`THINK_FLAGS=--limit-eval+500`). Results: `out.tar.gz` (JSON, logs), weights
(`adapter/`, `think_block.pt`) in `ckpt.tar.gz`.

## What comes out (`out/think/{arm}_s{S}/`)
- `result_{arm}_s{S}.json`: `{arm, seed, model, steps_stage1, steps_stage2, k_slots, params_trainable, train: {loss_curve, seconds,
  gate_log, dev_log, step_losses, gate_check}, aborted, eval: {validation|dev: {TAG: {acc, n, hits, row_offset}}}, label_nums}`.
  `hits` is a string of 0/1 in data-file order, so every comparison is paired. by_depth / by_bank / by_qtype are not stored;
  `summarize.py` recomputes them from the hits and the data files.
- Tags. a: `main` (dev, validation), `main_repeat` (validation, seed 0 only: same checkpoint, batches built shortest-first). b: `main`
  (3 loops) and `pass1` (1 loop). aplus, bplus: `main`. t: validation `L0 L1 L2 L4 L8 L12` (all 8,675 rows), `L16 L24` (first 2,000
  rows), `swap8 mean8 rep1_8 gatesoff8`; dev `L0 L1 L8`. t1: validation `L0 L1 L8`, dev `L1`. tw: validation `L1`.
- `adapter/` (a, b, aplus, bplus) or `think_block.pt` (t, t1, tw: board state dict).
- `python3 backbone/think/summarize.py out/think --data out/data [--json]` prints the report and every PREREG mark; run_box.sh writes it
  to `out/think/SUMMARY.txt`.

## think1.py
```
python3 backbone/think/think1.py --arm {a,b,aplus,bplus,t,t1,tw} --seed S --data out/data --out out/think/ARM_sS
    [--model Qwen/Qwen3.5-0.8B] [--max-len 2048] [--bsz 16] [--micro-bsz 4] [--limit-eval N] [--eval-bsz 64] [--eval-tokens 32768]
    [--a-adapter DIR] [--b-adapter DIR] [--no-cache] [--smoke]
```
Default adapters are `<parent of --out>/a_s{S}/adapter` and `.../b_s{S}/adapter`, i.e. `out/think/a_s{S}/adapter` in a normal run.
Extra flags for tests, not for the prereg run: `--steps N`, `--k N` (slots), `--gate-step N`, `--gate-enforce`, `--log-every N`.
Exit code 3 means the mechanics gate (or a NaN / divergence guard) aborted a board run; the result file is still written with
`"aborted": reason` and no evaluation.

Training dtype is bf16 on CUDA and fp32 on CPU; the board is always fp32; every arm uses `xent.fixed_cross_entropy` in fp32. Board
runs freeze the backbone and the LoRA and clip the gradient to 1.0 separately for the gates (lr 3e-3), for e0_hat + eta (5e-4) and for
the refiner (5e-4). Logs: a `[gate]` line every 10 steps (|tanh alpha|, cosine across questions and within a board, clamp fraction,
per-lap step size) stored in `train.gate_log`; every 250 steps `train.dev_log` gets answer CE and greedy accuracy at L = 1 and 8, the
swap lesion at 8, |tanh alpha| per layer and the refiner gradient norm, on the first 256 dev rows.

### Mechanics gate (t, t1, tw), exactly as coded
At step 150, abort if any of: mean |tanh alpha| over the 48 gates < 0.02; mean cosine of the same slot across the questions of the
16-row batch, final board (L = 8; L = 1 for t1 and tw), > 0.95; more than 90% of slots pinned at the clamp. At every step: a NaN loss or
gradient aborts; after step 20, a last-20-step mean loss above 2x the first-20-step mean aborts.
"Pinned at the clamp" is judged on `clamp5`: the share of slots whose RMS before the clamp exceeds 1.05 x rho, i.e. where the clamp
removes at least 5% of the update. The plain "any excess" share is also logged (`clamp`), but it is already 0.75-0.94 at initialisation
on the real model (slots start at about rho, so any update exceeds it), which would trip the gate before training does anything. This
choice is not spelled out in PREREG.md; fixed here before any run. At initialisation the cross-question cosine on the real model is
also about 0.993 (board.py probe), so the gate asks training to make the boards question-specific by step 150.
In `--smoke` the gate is computed (at step 4) and logged but not enforced, unless `--gate-enforce`.

## Tests (CPU, no GPU, no network)
```
HF_HOME=<cache> HF_HUB_OFFLINE=1 python3 backbone/think/test_think1.py [--real] [--only BOARD XENT S1 T8 TO TH TG TR SM]
python3 backbone/think/think1.py --smoke --data out/data --out /tmp/think-smoke   # all 7 arms end to end, then summarize
```
`test_think1.py` runs everything: board tests T1-T7, T9, T10 (+ read-patch identity, parameter count, API, bf16 smoke) from
`test_think1_board.py`, X1-X4 from `test_xent.py`, S1 from `test_summarize.py`, and T8 (same seed, identical 10-step stage-2 losses),
TO (data order), TH (hits in file order; gates off = arm a), TG (mechanics gate, abort path), TR (run_box.sh with a stub python) and SM
(the smoke run). `--real` adds the real-0.8B checks. The smoke run uses a tiny random qwen3_5 (8 layers, 2 full-attention), a byte
tokenizer, 20 rows of each split, 6 steps per stage, and writes to `OUT/smoke/{arm}_s{S}/`; about 1.5 minutes on 4 CPU cores. Its
accuracies are 0: it checks wiring, not learning.

## Files
`think1.py` harness; `board.py` the G-STS module (cache fork, gated read patch, think / answer / decode); `xent.py` fixed
cross-entropy; `summarize.py` marks; `run_box.sh` box script; `test_*.py` tests; `PREREG.md` marks; `DESIGN.md`, `RESEARCH.md`,
`SCALEUP.md`, `panel/`, `research/` reasoning.
