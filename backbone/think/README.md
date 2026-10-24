# Think-1: how to run it

A small trained "thinking block" (16 slots, a 2.6M-parameter refiner, zero-start gates) on a frozen Qwen3.5-0.8B + arm A's LoRA, against
plain LoRA (a, aplus) and the looped-layers arm (b, bplus). Marks are fixed in `PREREG.md`; design in `DESIGN.md`; code contract in
`IMPL-SPEC.md`. Village model only; the `test` split is never built or read. Every arm runs through ONE harness, `think1.py`.

## Ben's PC (RTX 5070 Ti 16 GB), one line, from the repo root
```
THINK_JOBS=a:0,b:0,aplus:0,t:0,t1:0 bash backbone/think/run_box.sh
```
Needs Python with CUDA torch and `pip install -r backbone/requirements.txt` (transformers 5.20.2, peft 0.21.2; `flash-linear-attention`
makes the Gated DeltaNet layers fast). The first run builds the village data into `out/data` (about 12 min on 4 cores). Everything is also
appended to `out/think/run.log`. The script stops with exit 2 if torch sees no CUDA GPU (`ALLOW_CPU=1` overrides: days, and not the same
hardware as the other arms). Then add the rest of seed 0 and look at `out/think/SUMMARY.txt`:
```
THINK_JOBS=tw:0 bash backbone/think/run_box.sh                       # diagnostic, seed 0 only (if seed 0 ran on Vast: unpack its ckpt.tar.gz + out.tar.gz here first, so a_s0's adapter is the same one)
THINK_JOBS=a:1,b:1,aplus:1,t:1,t1:1,a:2,b:2,aplus:2,t:2,t1:2 bash backbone/think/run_box.sh    # seeds 1 and 2
THINK_JOBS=bplus:0 bash backbone/think/run_box.sh                    # then, only if SUMMARY.txt says "bplus - b (seed 0) ... : yes", bplus:1,bplus:2
```
Seed 2 on Ben's PC with the jobs at once (`MAXPAR=2` on the 16 GB card keeps two processes in memory; the default is 3, which is near the limit of a 24 GB 3090 while three evals overlap: use `MAXPAR=2` there too until a real run records `peak_gpu_mem_gb` for t and tw):
```
THINK_JOBS=a:2,b:2,aplus:2,t:2,t1:2 PARALLEL=1 MAXPAR=2 bash backbone/think/run_box.sh
```
PREREG: bplus runs on all seeds only if bplus - b >= 1.0 at seed 0; `summarize.py` prints that difference and the yes / no. Seeds 1 and 2 may
run at the same time as seed 0 (PREREG amended 2026-10-24); the seed-0 futility rules are reported, and a stop applies only to seeds that
have not started. Re-running the same line skips every job whose result file exists.

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

## Vast (one RTX 3090 per seed, all of that seed's jobs at once)
`PARALLEL=1` runs the jobs of one box at the same time on its one GPU: first every listed stage-1 job (`a`, `b`), then, once their adapters
exist, every listed stage-2 job (`aplus`, `bplus`, `t`, `t1`, `tw`), never more than `MAXPAR` (default 3) processes at a time, with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` set. A stage-2 job starts only if its stage-1 job wrote its result (the adapter alone is saved before that job's eval), and a job with no result at the end of a stage (e.g. out of GPU memory) is run again alone, once. Each job writes
`out/think/{arm}_s{S}/run.log`; everything is also in `out/think/run.log`. Without `PARALLEL` the jobs run one after another, as before. For seed N
(N = 0, 1; seed 2 is on Ben's PC). Seed 0's box also runs `bplus:0` (it needs `b_s0`'s adapter, which is on that box); `tw:0` runs on Ben's PC.
The box is killed 10 minutes before its hours run out, losing every unfinished job, so the boxes get 12 hours:
```
python3 backbone/vast.py pack --out /tmp/think-s0 --slim --hours 12 --label claude-think1-compassionate-davinci-s0 \
    --env "THINK_JOBS=a:0,b:0,aplus:0,bplus:0,t:0,t1:0 PARALLEL=1 MAXPAR=2"
python3 backbone/vast.py pack --out /tmp/think-s1 --slim --hours 12 --label claude-think1-compassionate-davinci-s1 \
    --env "THINK_JOBS=a:1,b:1,aplus:1,t:1,t1:1 PARALLEL=1 MAXPAR=2"
python3 backbone/vast.py search --gpu "RTX 3090" --max-dph 0.15      # pick an offer ID; PREREG caps the two boxes at $3.60: 2 x 12 h x $0.15/h
python3 backbone/vast.py create --offer ID --args /tmp/think-sN/args.json --label claude-think1-compassionate-davinci-sN --disk 60
python3 backbone/vast.py status | logs ID | cat ID /job/tree/out/think/SUMMARY.txt
```
The hours are set at pack time (the box stops itself). Every box is the same GPU type, as PREREG wants per seed. `backbone/run_box.sh` installs
the dependencies, then hands over to `backbone/think/run_box.sh` when `THINK_JOBS` is set. Extra `think1.py` flags go in `THINK_FLAGS` joined with
`+` (`THINK_FLAGS=--limit-eval+500`). Results: `out.tar.gz` (JSON, logs), weights (`adapter/`, `think_block.pt`) in `ckpt.tar.gz`. Each result file
records the GPU name, dtype and the torch / transformers / peft / flash-linear-attention versions (`env`).

Kaggle T4s were probed (`backbone/think/probe_t4/`): fp16 is numerically fine, but a training step takes 28 s against 3.3 s on an A100, so they
are not used.

## What comes out (`out/think/{arm}_s{S}/`)
- `result_{arm}_s{S}.json`: `{arm, seed, model, steps_stage1, steps_stage2, k_slots, params_trainable, adapter_sha (arms that save an
  adapter), stage1_adapter_sha (arms that start from one), env: {gpu (name or "cpu"), dtype, torch, transformers, peft, flash_linear_attention
  (None if absent)}, train: {loss_curve, seconds,
  gate_log, dev_log, step_losses, gate_check}, aborted, eval: {validation|dev: {TAG: {acc, n, hits, row_offset}}}, label_nums}`.
  `hits` is a string of 0/1 in data-file order, so every comparison is paired. by_depth / by_bank / by_qtype are not stored;
  `summarize.py` recomputes them from the hits and the data files.
- Arms a and aplus are decoded by the board code with no board read (`board.prefill` of prompt[:-1] + `board.decode`, `slot_kv=None`, the same
  batches as `eval_board`: rows 0-1,999 and the rest sorted longest-first separately, no batch across row 2,000), so S(8) and A_ref are measured by identical code; b and bplus keep `train.greedy` (they need the looped runner).
- Tags. a: `main` (dev, validation), `main_repeat` (validation, seed 0 only: same checkpoint, batches built shortest-first). b: `main`
  (3 loops) and `pass1` (1 loop). aplus, bplus: `main`. t: validation `L0 L1 L2 L4 L8 L12` (all 8,675 rows), `L16 L24` (first 2,000
  rows), `swap8 mean8 rep1_8 gatesoff8 ref0` (`ref0`: the same batches decoded with no board read at all; `gatesoff8` must equal it row for row, while its gap to arm a's `main` is bf16 path noise, reported apart); dev `L0 L1 L8`. t1: validation `L0 L1 L8`, dev `L1`. tw: validation `L1`.
- `adapter/` (a, b, aplus, bplus) or `think_block.pt` (t, t1, tw: board state dict). Every result records the sha256 of the adapter
  weights it saved and of the stage-1 adapter it started from; `summarize.py` excludes (and says so) any dependent whose stage-1 hash is not
  the one its stage-1 arm's result carries, e.g. after arm a was retrained following a crash.
- `python3 backbone/think/summarize.py out/think --data out/data [--json]` prints the report and every PREREG mark; run_box.sh writes it
  to `out/think/SUMMARY.txt`.

## think1.py
```
python3 backbone/think/think1.py --arm {a,b,aplus,bplus,t,t1,tw} --seed S --data out/data --out out/think/ARM_sS
    [--model Qwen/Qwen3.5-0.8B] [--max-len 2048] [--bsz 16] [--micro-bsz 4] [--limit-eval N] [--eval-bsz 64] [--eval-tokens 32768]
    [--a-adapter DIR] [--b-adapter DIR] [--no-cache] [--no-lap-ckpt] [--smoke]
```
Default adapters are `<parent of --out>/a_s{S}/adapter` and `.../b_s{S}/adapter`, i.e. `out/think/a_s{S}/adapter` in a normal run.
Extra flags for tests, not for the prereg run: `--steps N`, `--k N` (slots), `--gate-step N`, `--gate-enforce`, `--log-every N`.
Exit code 3 means the mechanics gate (or a NaN / divergence guard) aborted a board run; the result file is still written with
`"aborted": reason` and no evaluation.

Training dtype is bf16 on CUDA and fp32 on CPU; the board is always fp32; every arm uses `xent.fixed_cross_entropy` in fp32. Board
runs freeze the backbone and the LoRA and clip the gradient to 1.0 separately for the gates (lr 3e-3), for e0_hat + eta (5e-4) and for
the refiner (5e-4). Logs: a `[gate]` line every 10 steps (|tanh alpha|, cosine across questions and within a board, the same cosines of the
board updates e_L - e_0, clamp fraction, per-lap step size) stored in `train.gate_log`; every 250 steps `train.dev_log` gets answer CE and greedy accuracy at L = 1 and 8, the
swap lesion at 8, |tanh alpha| per layer and the refiner gradient norm, on the first 256 dev rows.

### Memory (t, t1, tw)
Every slot pass and every answer pass runs under `torch.utils.checkpoint` (non-reentrant) during training, so only the small slot K/V and
the boards stay alive between laps and each pass is recomputed once in backward; the prompt cache is never written, so the recomputation
is exact (test TK: same loss and gradients, about 5x fewer saved bytes on the tiny model). `--no-lap-ckpt` turns it off. Before this, every
lap kept its activations until the one backward, about 0.65 GB per lap for 2 rows on the real 0.8B on CPU in fp32 (HF's non-fused
linear-attention fallback), and L_max = 12 with `--micro-bsz 2` ran out of 15 GB. GPU numbers are untested. If a board run still hits CUDA
out-of-memory, rerun with `MICRO=2` (or 1): the loss normaliser is the whole step's answer-token count, so a smaller micro-batch gives the
same gradient up to rounding. Install `flash-linear-attention` first.

### Mechanics gate (t, t1, tw), exactly as coded
Aborts (exit 3, result file with `"aborted"`, no evaluation) only on: mean |tanh alpha| over the 48 gates < 0.02 at step 150 (the gates
never opened); a NaN loss or gradient at any step; after step 20, a last-20-step mean loss above 2x the first-20-step mean.
Logged every 10 steps, never aborts (PREREG amended 2026-10-24 before any run): the cross-question cosine of the final boards and of their
updates e_L - e_0 (`cos_across`, `cos_update_across`; within a board: `cos_within`, `cos_update_within`), and the share of slots at the rms
clamp (`clamp`: any excess; `clamp5`: pre-clamp RMS above 1.05 x rho, where the clamp removes at least 5% of the update). On the real model
every board starts from the same e_0 at the clamp, so the final-board cosine is about 0.99 and about 94% of slots sit at the clamp at step 0;
for one refinement (t1, tw) the cosine cannot fall much below 0.97 whatever training does (saturated random-sign updates on the real e_0,
16 rows: 0.990 at eta 0.10, 0.974 at 0.16, 0.961 at 0.20; `eta` can move only ~0.06 by step 150), so these could not be abort rules. The update cosine is the one that says whether boards are question-specific.
In `--smoke` the gate is computed (at step 4) and logged but not enforced, unless `--gate-enforce`.

## Tests (CPU, no GPU, no network)
```
HF_HOME=<cache> HF_HUB_OFFLINE=1 python3 backbone/think/test_think1.py [--real] [--only BOARD XENT S1 T8 TO TH TG TR SM]
python3 backbone/think/think1.py --smoke --data out/data --out /tmp/think-smoke   # all 7 arms end to end, then summarize
```
`test_think1.py` runs everything: board tests T1-T7, T9, T10 (+ read-patch identity, parameter count, API, bf16 smoke) from
`test_think1_board.py` (TK: lap checkpointing equals plain, clamp gradient at a zero slot, penalty definition), X1-X4 from `test_xent.py`, S1 from `test_summarize.py`, and T8 (same seed, identical 10-step stage-2 losses),
TO (data order), TH (hits in file order; gates off = arm a), TG (mechanics gate, abort path), TR (run_box.sh with a stub python, CUDA check, PARALLEL ordering and MAXPAR cap) and SM
(the smoke run). `--real` adds the real-0.8B checks. The smoke run uses a tiny random qwen3_5 (8 layers, 2 full-attention), a byte
tokenizer, 20 rows of each split, 6 steps per stage, and writes to `OUT/smoke/{arm}_s{S}/`; about 1.5 minutes on 4 CPU cores. Its
accuracies are 0: it checks wiring, not learning.

## Files
`think1.py` harness; `board.py` the G-STS module (cache fork, gated read patch, think / answer / decode); `xent.py` fixed
cross-entropy; `summarize.py` marks; `run_box.sh` box script; `test_*.py` tests; `PREREG.md` marks; `DESIGN.md`, `RESEARCH.md`,
`SCALEUP.md`, `panel/`, `research/` reasoning.
