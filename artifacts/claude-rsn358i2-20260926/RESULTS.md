# rsn-358i2 RESULTS (builder, BensPC, 2026-09-26)

## Verdict: SUSPECT CONFIRMED

V0 PASS, M1 PASS, M2 PASS, M3 PASS. The proved-wrong clause is NOT triggered.
358i's loop learns at plain speed and closes the grid gap when its block layers
actually receive gradient (cache_enabled=False). 358d, 358i and 358x stay
registered as they are (addendum suggestion from PASSMARKS applies, not a rewrite).

## Registered marks (PASSMARKS.md, plain = 358i's own runs/plain-s{1..4}/tests.json on origin/main)

- **V0 validity: PASS.** steps_block_nograd = 0 in every train_summary.json
  (s1 0, s2 0, s3 0, s4 0; steps_seen 60000 on all 4). The fix took.
- **M1 learning speed: PASS.** dev grids5 at step 10,000 (train-log dev, /200):
  s1 195, s2 198, s3 197, s4 200. 4 of 4 seeds >= 100 (needs >= 3).
  (358i loop: 0/1/2/1. 358a loop BensPC: 176/163. 358i plain: 160-174.)
- **M2: PASS.** 4-seed mean loop - plain on grids5 = +1.00 (>= -10). 358i: -77.5.
- **M3: PASS.** 4-seed mean loop - plain on grids6 = +51.75 (>= -10). 358i: -83.
- **Suspect confirmed = V0, M1, M2 and M3: all four hold.**
- **Proved wrong (dev grids5@10k <= 20/200 on >= 3 of 4 seeds AND mean
  loop-plain grids5 <= -50): NOT triggered.** dev@10k <= 20 on 0 of 4 seeds
  (values 195/198/197/200); mean gap +1.00.

## Per-seed table, every test (/300; gap = loop - plain; means over 4 seeds)

| test | loop s1 s2 s3 s4 | plain s1 s2 s3 s4 | gap s1 s2 s3 s4 | loop mean | plain mean | gap mean |
|---|---|---|---|---|---|---|
| sums4 | 300 300 300 300 | 300 300 300 300 | 0 0 0 0 | 300.00 | 300.00 | +0.00 |
| sums6 | 299 299 298 297 | 188 209 177 217 | +111 +90 +121 +80 | 298.25 | 197.75 | +100.50 |
| sums8 | 273 274 276 278 | 133 116 65 146 | +140 +158 +211 +132 | 275.25 | 115.00 | +160.25 |
| grids5 | 300 300 300 300 | 299 300 297 300 | +1 0 +3 0 | 300.00 | 299.00 | +1.00 |
| grids6 | 292 296 283 287 | 230 248 237 236 | +62 +48 +46 +51 | 289.50 | 237.75 | +51.75 |
| grids7 | 186 241 173 177 | 136 149 130 142 | +50 +92 +43 +35 | 194.25 | 139.25 | +55.00 |
| numbers4 | 2 0 0 2 | 0 0 2 3 | +2 0 -2 -1 | 1.00 | 1.25 | -0.25 |
| numbers5 | 1 0 1 0 | 0 0 1 1 | +1 0 0 -1 | 0.50 | 0.50 | +0.00 |
| sums10 | 219 244 232 250 | 93 60 27 112 | +126 +184 +205 +138 | 236.25 | 73.00 | +163.25 |
| sums12 | 164 202 193 198 | 65 44 7 89 | +99 +158 +186 +109 | 189.25 | 51.25 | +138.00 |

## Dev grids5 (/200) at fixed steps per seed (train_log.jsonl dev field)

| seed | 5k | 10k | 20k | 40k | 60k |
|---|---|---|---|---|---|
| s1 | 91 | 195 | 197 | 199 | 200 |
| s2 | 86 | 198 | 200 | 200 | 200 |
| s3 | 88 | 197 | 200 | 200 | 200 |
| s4 | 65 | 200 | 199 | 199 | 200 |

## steps_block_nograd per seed (train_summary.json): s1 0, s2 0, s3 0, s4 0.

## Report-only

- sums6/8/10/12, grids7, numbers: see per-seed table above.
- Loop at fixed rounds (/300):
  - sums6: s1 1=255 2=270 4=291 8=299 12=299 16=299 24=299 32=298 48=298 (meanr 8.22);
    s2 255 276 295 298 299 299 299 299 299 (7.94);
    s3 252 273 297 298 298 298 298 298 298 (7.89);
    s4 276 276 295 295 297 297 297 297 297 (7.22).
  - grids5: s1 91 204 298 300 300 300 300 300 300 (10.09);
    s2 109 200 299 300 300 300 300 300 300 (10.22);
    s3 86 198 298 300 300 300 300 300 300 (10.03);
    s4 83 197 298 300 300 300 300 300 300 (10.35).
  - grids6: s1 53 142 243 288 291 292 292 292 292 (12.97);
    s2 60 143 253 292 292 295 296 296 296 (12.61);
    s3 46 145 249 283 279 282 282 285 283 (14.45);
    s4 44 132 258 283 285 285 286 287 287 (15.34).
  - mean rounds sums6 > sums4 on all seeds (8.22/7.94/7.89/7.22 vs 6.81/6.81/6.63/6.43).
- Seed 4 column: see per-seed table (s4: 300/297/278/300/287/177/2/0/250/198).
- 358t-style G0-G3 against plain (report only, beside 358i):
  - G0 validity: MET. Every seed, loop right >= 210/300 on 2 of 3 practised-size
    kinds (sums4 300, grids5 300, numbers4 0-2), and plain right >= 210/300 on 2
    of 3 kinds (sums4 300, grids5 297-300, numbers4 0-3). Loop "right" used for
    "loop EMA" (358i2 eval has no EMA arm; adaptation, no effect on verdict).
  - G1 bigger: MET. Mean gaps sums6 +100.50, grids6 +51.75 (>= +30 on 2 of 3),
    numbers5 +0.00 (>= -10 on the third). On 4 of 4 seeds loop-plain > 0 on both
    sums6 (+111/+90/+121/+80) and grids6 (+62/+48/+46/+51).
  - G2 practised: MET. Mean gaps sums4 +0.00, grids5 +1.00, numbers4 -0.25
    (all >= -10).
  - G3 stop: MET. On 4 of 4 seeds loop right >= fixed-16 right - 5 on each bigger
    test (sums6: 299/299/298/297 vs 299/299/298/297; grids6: 292/296/283/287 vs
    292/295/282/285; numbers5: 1/0/1/0 vs 2/0/1/0), and mean rounds sums6 > sums4.
- Grad-norm table (train_summary.json grad_norms, per-block gradient norm every
  2500 steps; block Linear matrices only):
  - s1: step1 3.45963/3.51654; 2500 0.229921/0.259018; 5000 0.338161/0.399585;
    7500 0.158243/0.152439; 10000 0.006093/0.006581; 12500 1.266438/0.996353;
    15000 0.309411/0.180544; 17500 0.010198/0.01137; 20000 0.083804/0.077304;
    22500 0.066595/0.09391; 25000 0.089583/0.032968; 27500 0.001034/0.001408;
    30000 8.4e-05/9.5e-05; 32500 0.531412/0.331834; 35000 0.014306/0.017748;
    37500 0.000143/0.000142; 40000 2.9e-05/3.3e-05; 42500 0.000135/0.00019;
    45000 3.3e-05/4.9e-05; 47500 4.9e-05/6.2e-05; 50000 0.001545/0.001542;
    52500 0.105614/0.095107; 55000 0.001915/0.001604; 57500 4.1e-05/5.1e-05;
    60000 9.9e-05/0.000102 (block0/block1).
  - s2: step1 2.836914/2.73902; 2500 1.407848/1.125702; 5000 0.498181/0.730187;
    7500 1.182315/1.109813; 10000 0.237737/0.211178; 12500 0.000834/0.000829;
    15000 0.087553/0.106766; 17500 0.022395/0.023254; 20000 0.283174/0.253033;
    22500 0.010036/0.009292; 25000 0.000985/0.000898; 27500 0.024313/0.025804;
    30000 0.052171/0.07835; 32500 0.058367/0.06548; 35000 0.045221/0.045444;
    37500 0.00013/0.000116; 40000 0.002239/0.00242; 42500 0.000114/0.00014;
    45000 0.067484/0.056684; 47500 0.001457/0.001372; 50000 0.000143/0.000161;
    52500 3.9e-05/4.3e-05; 55000 3.6e-05/4e-05; 57500 0.000131/0.000148;
    60000 2.6e-05/2.5e-05.
  - s3: step1 2.538635/2.503935; 2500 0.448313/0.474434; 5000 0.474356/0.439072;
    7500 0.551768/0.532034; 10000 0.248839/0.265284; 12500 0.000672/0.000846;
    15000 0.000471/0.000667; 17500 0.090528/0.098499; 20000 0.381158/0.271525;
    22500 0.01165/0.009954; 25000 0.000995/0.000976; 27500 7.1e-05/8.3e-05;
    30000 0.000415/0.000456; 32500 0.067118/0.10405; 35000 0.001889/0.001679;
    37500 9.8e-05/9.9e-05; 40000 0.001373/0.001676; 42500 0.000225/0.000251;
    45000 8.3e-05/0.000112; 47500 6.8e-05/6.3e-05; 50000 4e-06/5e-06;
    52500 0.176757/0.13256; 55000 3.2e-05/3.4e-05; 57500 1.8e-05/2e-05;
    60000 0.033634/0.015535.
  - s4: step1 2.506944/2.446991; 2500 0.152504/0.173848; 5000 0.017737/0.015919;
    7500 0.00976/0.012858; 10000 0.338132/0.344824; 12500 0.441314/0.323018;
    15000 0.063282/0.0874; 17500 0.405429/0.432627; 20000 0.02831/0.038326;
    22500 0.104425/0.132831; 25000 0.003711/0.005367; 27500 0.207135/0.226523;
    30000 0.000802/0.000821; 32500 0.087631/0.08311; 35000 0.040636/0.033252;
    37500 0.003159/0.003289; 40000 0.00295/0.001861; 42500 2.5e-05/2.5e-05;
    45000 3.3e-05/3.9e-05; 47500 8.6e-05/8.9e-05; 50000 2.7e-05/3.9e-05;
    52500 5.7e-05/7.3e-05; 55000 3.9e-05/4e-05; 57500 0.06224/0.042776;
    60000 3.2e-05/3.8e-05.

## Machine, versions, minutes

- Machine: BensPC (per ADDENDUM-1-benspc.md). GPU: NVIDIA GeForce RTX 5070 Ti.
- torch 2.11.0+cu128, CUDA 12.8 (train_summary.json on all 4 seeds), python 3.10.9.
- Minutes per run (train-process "min" at step 60000): s1 102.8, s2 104.8,
  s3 104.9, s4 104.8. Wall: seeds 1-2 launched ~17:33-17:35Z, seeds 3-4 ~17:41Z;
  s1 done ~19:16Z, s2/s3/s4 done by ~19:35Z. Evals ~2-4 min each after training.
- nvidia-smi snapshots: start 212 MiB used / 15784 MiB free, 0%, 12.5 W (only
  desktop processes); 2 seeds 6938/9058 MiB, 76%, 181 W; 4 seeds 13176/2820 MiB,
  94%, 192 W (no spill signature); end 229/15767 MiB, 0%. Free disk C: 8.49 GB
  at start (above the 5 GB stop line).
- Cost $0 (BensPC). Elapsed ~2.5 h of the 8 h cap.

## Stage 0 (report only, whole outputs)

torch version line:

```text
2.11.0+cu128 12.8
```

scripts/claude_stage0_autocast_grad.py:

```text
torch 2.11.0+cu128 cuda
loop  free=3 grad=2 cache=True : block weight matrices with no gradient 0/12
loop  free=3 grad=2 cache=False: block weight matrices with no gradient 0/12
loop  free=0 grad=2 cache=True : block weight matrices with no gradient 0/12
loop  free=0 grad=2 cache=False: block weight matrices with no gradient 0/12
plain free=0 grad=2 cache=True : block weight matrices with no gradient 0/48
plain free=0 grad=2 cache=False: block weight matrices with no gradient 0/48
```

As ADDENDUM-1 expected on torch 2.11, both lines show 0/12; the job did NOT stop.

## Checks (whole outputs)

- `python -B scripts/claude_rsn358a_envs.py selftest`:
  `selftest ok: 1362 four-hands (1062 practice, 300 held out), 1346 three-hands`
- `python -B scripts/claude_rsn358i2_run.py selftest`:
  `selftest ok: torch 2.11.0+cu128, cache off, 0/8 block Linear weights without gradient after 3 free + 2 graded rounds`
- `python -B scripts/claude_rsn358i2_run.py check-mask`:
  `check-mask ok: narrow heads 0-3 ignore cells 2+ columns away; wide heads 4-7 unchanged`

## Seal

- SEAL-code.sha256.txt: 19/19 OK on BensPC (sha256sum -c under Git Bash).
- SEAL-run.sha256.txt (64 hex each, verified length): final.pt sealed BEFORE eval.
  - d30887c59f57496a1a195d7250e130bb1c51393d973ce45f4bdd898ba5eb8261  W/loop-s1/final.pt
  - 4085df22366b96190b087a7b46333daec9f19d078332ea5bf6328a15f2ed6594  W/loop-s2/final.pt
  - 5d571cc276d88f5af5da34c79e0d198878f9e674888b2150107095e27adc4a7a  W/loop-s3/final.pt
  - f0a84b11d1722d97739a5999f3b2b487c0bc09dc1c927fde14e6566adedd6621  W/loop-s4/final.pt
- Mac copies at ~/premonition-models/rsn358i2/loop-s{1..4}/final.pt re-hashed:
  all 4 match (64 hex). BensPC copies kept at
  C:/Users/benja/premonition-models/rsn358i2/loop-s{1..4}/final.pt
  (25,764,244 bytes each). No weights in git.
- Each eval ran exactly once per checkpoint file (4 evals, 4 checkpoints).

## Every deviation

1. Machine is BensPC per ADDENDUM-1 (expected, disclosed): torch 2.11.0, not the
   2.8 rental; plain reference trained on a 2.8 rental (unaffected by the bug;
   audit logs show plain learning at the same speed on both machines).
2. Stage 0 report-only per ADDENDUM-1 (did not stop; 0/12 on both lines).
3. C:\Users\benja\GPU-BUSY.txt already existed naming this same job
   (claude-sleep-358i2pc, since 2026-09-26T17:17:09Z) before the first check; it
   named this job, not another, so the run proceeded; left in place; deleted at
   the end. No other GPU job ran concurrently (nvidia-smi showed desktop processes only).
4. Detached launch via Win32_Process Create + cmd /c wrapper with >> log 2>&1
   (one combined log per seed, as specified); recorded PIDs are the cmd parents
   (s1 10348, s2 3576, s3 13828, s4 17048).
5. First seed-1 attempt (Git-Bash nohup) produced a coupled venv-parent +
   base-interpreter worker pair sharing one out dir; while diagnosing I killed the
   apparently comatose parent (exact PID) and the worker died with it at step
   ~11000 (min 7.3). Seed 1 was restarted clean to the same out dir after deleting
   only its partial outputs (W/loop-s1.log, W/loop-s1/train_log.jsonl, BensPC
   scratch). All accepted results come from the clean restarts. No test items
   touched at any point.
6. Seeds 1+2 launched ~2 min apart (not the same second); seeds 3+4 launched after
   the 5-minute gate with 9058 MiB free (>= 5 GB). 15-minute projection showed all
   four finishing inside the cap, so no TOO-SLOW stop (seed 4 finished, CONCLUSIVE).
7. selftest/check-mask outputs carry detail suffixes after the required phrases
   (quoted whole above); accepted as pass.
8. Evals ran sequentially after all training finished (GPU free), same command,
   once per checkpoint.
9. train_summary.json records python 3.10.9 (venv and base report the same torch
   build 2.11.0+cu128; launches invoked the specified lis300 venv python path).
10. G0 "loop EMA" read as loop "right" (358i2 eval has no EMA arm); report-only.
11. Disk 8.49 GB free at start (above stop line, noted, no action).
12. No installs, no model downloads, sealed code never edited (19/19 seal match
    before training; breakage rule never triggered on accepted runs).

## What this means / does not mean

The autocast weight cache was the thing stopping 358i's loop from learning: with
the cache off, the loop reaches plain-level dev speed by step 10k on all 4 seeds
and beats 358i's plain on every bigger/generalisation test while matching it on
practised sizes. It does NOT mean the loop is better in general: numbers4/5 are
0-2/300 on both arms (neither learned them), and plain was trained on a different
machine/torch. What is proved: on BensPC, 358i's loop with cache off trains its
layers (V0: 0 blocked steps of 60000 x4) and the grid gap disappears.
