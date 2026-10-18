# Swarm screen box kit: build contract (Opus layer -> Sonnet coder), 2026-10-18

Status: DRAFT until the coordinator review (Q26) passes. $0 work: code + a CPU dry run. NO rental, no GPU.
The coordinator granted C0 + S0 in principle (Q28, hard cap $4.20) but nothing books until the review passes,
the card is sealed, and this kit's CPU dry run shows every mark computable (house sealing rule, as GR4 §9).

House model to copy (read with `git show origin/claude/launch-bound-solve:<path>`):
`results/8a-g/speedup/launch/PREREG-launch-defer.md` (§1 bench protocol, §6 money), `results/8a-g/speedup/launch/dry_gr4.sh`,
`results/8a-g/speedup/launch/dryrun-gr4/dry_marks.md` / `dry_marks.json` (readout shape).

Cards this kit serves: `design/swarm/RUNCARD-S0.md` (book first) and `RUNCARD-S1.md` (readout only; S1 is NOT booked).

## Files (new; do not edit anything else except the one train.py line in §5)

* `scripts/premonition_swarm_screen.py`: the runner; subcommands below. Plain argparse, JSON out, logs to stdout.
* `scripts/premonition_swarm_marks.py`: the readout; computes every mark of a card from the runner's JSON files.
* `scripts/premonition_swarm_box.sh`: the box script (bash, `set -euo pipefail`).
* `tests/test_premonition_swarm_screen.py`: unit tests (CPU, < 60 s, no data files).
* `artifacts/claude-swarm-screen-20261018/dryrun/`: the CPU dry run's outputs + `DRYRUN.md`. Keep it small
  (< 5 MB; drop checkpoints, keep JSON and logs).

## Arms

```
ARMS = {"D1": {}, "S0": dict(thinkers=4, swarm_board=False, swarm_rounds=4, board_cards=16),
        "S1": dict(thinkers=4, swarm_board=True, swarm_rounds=4, board_cards=16)}
C0_ARMS = {"D1": {}, "S0m2": dict(thinkers=2), "S0m4": ARMS["S0"], "S0m8": dict(thinkers=8), "S1m4": ARMS["S1"]}
```
(swarm_rounds 4 / board_cards 16 are the config defaults; spell them out anyway.)

## Runner subcommands (`python -B scripts/premonition_swarm_screen.py <cmd> ...`)

Common options: `--root` (project root; default the repo), `--device cpu|cuda`, `--size full|tiny` (tiny = dry run only),
`--out <file.json>`. Budget: copy `make_budget()` from `scripts/premonition_pointer_ablation.py` (same RUNTIME handling).

1. `data --visits large|tiny` -> `step1.build_data(budget, visits=..., seed=0, workers=...)`; writes `{data_rel, tag,
   tokenizer_path, tokenizer_sha256}`. Use the v2 tokenizer: figure out from `premonition/train.py:train_d`,
   `premonition/exp1.py:open_data`, `premonition/identity.py` and `data/tokenizer/` which path D label-free runs need
   (`VOCAB_V2` = 7068, `premonition-tok-v2*.json`); assert the vocab size you get is 7068 for `--size full`.
   If build_data's own tokenizer differs from the one train_d/exp1 need, say so in your report instead of guessing.
2. `c0 --data-rel --tokenizer --rounds 3 --warmup 10 --timed 40 --chunk 5` (GR4 bench protocol, warm stretch only):
   * For each round r in 1..3, for each arm in `C0_ARMS` in a fixed interleaved order, for each mode in
     ("gold", "teacher", "own" with p_own 0.75): a FRESH model + `MiniTrainer` (seed 0, `mini_train_config()`),
     the SAME fixed list of batches (from `pdata.batches(train_cache, 55_000, seed=0, max_visits=48)`, label-free,
     drawn once), `warmup` untimed `_train_step`s then `timed` timed ones in chunks of `chunk`;
     `torch.cuda.synchronize()` around each chunk on CUDA. Round value = median chunk s/update; arm-mode value =
     median over rounds. Record peak allocated memory per arm.
   * Curriculum-weighted s/update per arm: 0.05 gold + 0.25 teacher + 0.70 own.
   * D1's FLOP fit: `trainer.calibrate(4 head batches)`; curriculum-weighted FLOPs/update from the fit and
     `planned_loops`; D1 FLOP/s = that / D1 weighted s/update. `T_raw = 2.6e16 / D1_flops_per_s`;
     `T = min(3600, 300 * ceil(T_raw / 300))` (RUNCARD-S0 §1). With `--size tiny` use `--t-override` (dry run: 30).
   * GPU-busy fraction (CUDA only, else null): `torch.profiler` over 10 own-mode updates for D1 and S0m4:
     sum of CUDA kernel self time / wall time.
   * **Stop-and-ask (FUNDING-BID C0 rule):** `ratio = S0m4 weighted s/update / D1 weighted s/update`;
     `stop_and_ask = ratio > 2.5`. Also `money_stop = projected S0 box-hours x dph > 3.50` where projected
     S0 box-hours = (6 x T + 6 x measured-eval-estimate) / 3600 x 1.15 and dph comes from `--dph` (box: the billed
     rate). Write both flags and their inputs into c0.json.
3. `train --arm D1|S0|S1 --seed N --seconds T --data-rel --tokenizer` -> `premonition.train.train_d(budget,
   data_rel=..., tokenizer_path=..., flop_budget=1e30, seconds_budget=T, swarm=ARMS[arm] or None, seed=N,
   device=..., size=..., eval_every=0, checkpoint=f"checkpoints/swarm-screen/{arm}-s{N}")`; write the report JSON
   (drop "history" bulk except the last 5 records; keep everything else).
4. `eval --checkpoint <rel> [--lesion board|notes|cards]` -> `evaluate_d_checkpoint(budget, ckpt, split="validation",
   device=..., lesion=...)`; write the JSON (it already has per-item `id/correct/decision/slices`).

## train.py (the ONE allowed edit)

`MiniTrainer.train`'s return dict: add `"train_seconds": self.train_seconds` only when `self.seconds_budget is not None`
(flag-off reports unchanged). M5 reads it.

## Readout (`scripts/premonition_swarm_marks.py --card S0|S1 --dir <outputs> --out MARKS-S0.json`)

Input files: `c0.json`, `train-{arm}-s{seed}.json`, `eval-{arm}-s{seed}.json`, `eval-S1-s{seed}-{lesion}.json` (S1).
Seeds 0, 1, 2. Writes `MARKS-<card>.json` and a human `MARKS-<card>.md` (one table row per mark, then one VERDICT line).

* **Cell membership**: read `premonition/exp1.py` and reproduce EXACTLY how `summary.decision_cells[name]` is built
  from items (`decision` flag, `slices` list, exclusions). Then ASSERT, per eval file and cell, that your recomputed
  accuracy equals the file's own `decision_cells` value; any mismatch -> verdict **VOID (schema)**.
* Pairing: by item `id` within a seed; pooled = concatenation over seeds of the per-seed paired vectors. The item id
  sets of the two arms of a seed must be identical (else VOID).
* p-values: `learnlab.metrics.paired_greater_pvalue(a, b, margin=0.0)` (default samples/seed); alpha 0.01.
* **S0 marks** (RUNCARD-S0 §3), with D1 = control:
  - M1: pooled Δ(far_deep) = mean(S0) − mean(D1) ≥ 0.030 AND p(S0 > D1) < 0.01 AND per-seed Δ > 0 on ≥ 2 of 3.
  - M2 (DEV slip, per seed, NEVER averaged): seed slips on near if S0_near < D1_near − 0.030; same for overall,
    separately. M2 fails if near slips on ≥ 2 of 3 seeds OR overall slips on ≥ 2 of 3 seeds.
  - M3: per seed from `directories.validation.retrieval.swarm`: ok iff every `ask_rate` ≥ 0.05 and
    min(`fetch_count`) ≥ 0.10 × max(`fetch_count`). M3 passes iff ok on ≥ 2 of 3 seeds.
  - M4: `collapsed` per seed; collapsed on ≥ 2 of 3 seeds -> the verdict line must contain
    "COLLAPSED: the desks are copies". Print fetch_overlap, register_cos, ask_rate[4], fetch_count[4], silent_desks.
  - M5 (validity): every train report `status == "completed"`, `train_seconds` within T ± 2% (T from c0.json),
    final logged loss finite; one data tag and one tokenizer sha256 across all files.
  - M6: `far_deep` has ≥ 100 items in every eval file, else INSUFFICIENT.
  - KILL condition: pooled Δ(far_deep) ≤ 0 OR per-seed Δ < 0 on ≥ 2 of 3.
  - **Verdict precedence** (fixed here; mirrored into the card before sealing): VOID > INSUFFICIENT > KILL > FAIL
    (M2 or M3) > PROMOTE (M1 and not collapsed) > HOLD. If collapsed and M1 passes: HOLD with the COLLAPSED text.
* **S1 marks** (RUNCARD-S1 §3), S0 = control, D1 = forgetting reference: M1 as S0-M1 with (S1, S0);
  M2 board used: pooled Δ(S1 intact − S1 lesion=board) ≥ 0.030, p < 0.01, positive on ≥ 2 of 3, else FAIL
  (BOARD-UNUSED); M3 = S0-M2 with (S1, D1); M4 = S0-M3; M5 = S0-M4 plus: if S1 collapsed on ≥ 2 of 3 and S0 not ->
  "the board collapsed the desks", no PASS; M6 = validity + cells. Verdicts VOID > INSUFFICIENT > KILL-COMM > FAIL > PASS > HOLD.
  Information rows: notes/cards lesion drops, S1 vs D1 far_deep, depth_2..depth_5 cells, changed slice.

## Box script (`scripts/premonition_swarm_box.sh`)

Env: `PIN` (the sealed commit), `DPH` (billed $/h), `MAXH` (default 8.0), `CAP` (default 4.20), `PART` (`c0` | `s0` | `all`,
default `all`), `DRYRUN` (1 = CPU tiny dry run). Steps, each logged with UTC timestamps to `box.log`:
1. Refuse unless `git rev-parse HEAD == PIN` and every file in `scripts/premonition_swarm_manifest.txt`
   (sha256 list, written by `premonition_swarm_screen.py manifest` over: premonition/{config,model,swarm,train,store,
   batch,data,exp1,slices}.py, the three scripts) matches. Refuse if `MAXH * DPH > CAP` (skip in DRYRUN).
2. Host record: `nvidia-smi -q`, torch/CUDA versions, hostname -> `host.txt` (DRYRUN: whatever exists).
3. `data` (large; DRYRUN: tiny).
4. `c0` -> `c0.json`. If `stop_and_ask` or `money_stop`: write `STOP-AND-ASK.txt` with the numbers and EXIT 3 before
   any training. (PART=c0 stops here regardless.)
5. Trains, interleaved, one at a time: D1 s0, S0 s0, D1 s1, S0 s1, D1 s2, S0 s2 (`--seconds T` from c0.json;
   DRYRUN T = 30, size tiny, device cpu).
6. Evals of all six checkpoints.
7. `premonition_swarm_marks.py --card S0` -> MARKS-S0.{json,md}.
8. Tar every JSON/log/MARKS file (not checkpoints) to `swarm-screen-out.tgz` for copy-back; print its sha256.
Never destroys the box (the rental agent does that after a checked copy-back).

## CPU dry run (run it here)

`DRYRUN=1 PIN=$(git rev-parse HEAD) bash scripts/premonition_swarm_box.sh` with outputs under
`artifacts/claude-swarm-screen-20261018/dryrun/`. Because the dry run cannot have a committed manifest for an
uncommitted tree, DRYRUN may regenerate the manifest first and must say so in box.log. The dry run must reach step 8
with every mark COMPUTED (any verdict is fine; tiny numbers mean nothing and are NOT a peek at the screen). If a mark
cannot be computed (e.g. M6 INSUFFICIENT because tiny validation has < 100 far_deep items), the readout must still
compute every other mark and report INSUFFICIENT honestly; in DRYRUN add `--min-items 1` so the full verdict path
is also exercised in a second readout pass, and record both in `DRYRUN.md`. Also run the S1 readout on the dry run
(train + eval an S1 tiny arm for 3 seeds and the 3 lesions) so `MARKS-S1` is proven computable too.
Write `DRYRUN.md`: commands, wall times, which marks computed, both verdict lines, file list with sizes.

## Tests (`tests/test_premonition_swarm_screen.py`)

Synthetic eval/train/c0 JSON (no data): each S0 verdict branch (VOID schema mismatch, VOID seconds, INSUFFICIENT,
KILL, FAIL-M2 per-seed-not-averaged case where the 3-seed mean slips but only 1 seed does -> no FAIL, FAIL-M3,
PROMOTE, HOLD, COLLAPSED-blocks-PROMOTE), the S1 BOARD-UNUSED branch, the T formula (rounding, 3600 cap), and the
stop-and-ask / money_stop flags. Then run `python -m unittest tests.test_premonition_swarm_screen
tests.test_premonition_swarm tests.test_premonition_model tests.test_premonition_train` and report counts.
