# dl-9 GPU build (BensPC): RESULTS-gpu

Verdict: PASS (H1, H2, H3, H4 all true; proved_wrong false; not INCONCLUSIVE: L0 = 54 >= 10, S night-7 lost sum = 47 >= 20).

## Marks block, exactly as the script printed at the end of gpu/log.txt

{
 "L0": 54,
 "final_lost": {
  "S": [
   20,
   27
  ],
  "X": [
   0,
   0
  ],
  "R": [
   5,
   8
  ]
 },
 "final_lucky": {
  "S": [
   231,
   283
  ],
  "X": [
   231,
   283
  ],
  "R": [
   111,
   133
  ]
 },
 "gain_over_L0": {
  "S": [
   177,
   229
  ],
  "X": [
   177,
   229
  ],
  "R": [
   57,
   79
  ]
 },
 "switch_test_on": [
  100,
  100
 ],
 "switch_panel_on": [
  0,
  0
 ],
 "H1 forgetting stopped: X lost <= 5 on each seed, and X lost <= 0.25 x S lost (sums)": true,
 "H2 learning kept: X gain >= 0.9 x S gain on each seed": true,
 "H3 switch learned: on for >= 95% of TEST puzzles and off for >= 95% of panel items, each seed": true,
 "H4 choosing beats chance: X gain >= 2 x R gain and X lost <= R lost (sums)": true,
 "verdict": "PASS",
 "proved_wrong": false
}

Marks arithmetic check (integer counts): H1: X lost 0 and 0 (each <= 5); sums X 0 <= 0.25 x S 47 = 11.75. H2: X gain 177 >= 0.9 x 177 = 159.3; 229 >= 0.9 x 229 = 206.1. H3: test_on 100 and 100 (each >= 95 of 100); panel off 300 and 300 (each >= 285 of 300). H4: X gain sum 406 >= 2 x R gain sum 136 = 272; X lost sum 0 <= R lost sum 13. Proved-wrong: X lost sum 0 > 0.5 x S lost sum 47? No. X gain < 0.8 x S gain on either seed? No (equal on both).

## Setup rows (before night 1)

- pool: asked 1000, questions 501, train 400, held 101, with_suffix 260.
- base: lucky 54, reached 27, greedy 2, harm_right 201, reworded_greedy [2, 2, 4, 2]. L0 = 54.

## Per-seed night table (every night, from the [dl9] night lines)

Columns: lucky / reached / greedy / harm lost / harm gained. Switch: test_on (of 100 TEST) / panel_on (of 300) / by kind bigger,capital,count,opposite,order,plural / held_neg_on (of 101). kl_S = S adapter KL to base. S on = 400 every night.

### Seed 16

| night | S lucky/reached/greedy/lost/gained | X lucky/reached/greedy/lost/gained/on | R lucky/reached/greedy/lost/gained/on | switch test_on/panel_on/by-kind/held_neg_on | kl_S | minutes |
|---|---|---|---|---|---|---|
| 1 | 139/52/12/8/53 | 139/52/12/0/38/188 | 95/39/5/4/32/188 | 100/88/bigger 86, capital 0, count 2, opposite 0, order 0, plural 0/0 | 0.12589 | 10.1 |
| 2 | 180/54/17/11/50 | 180/54/17/0/0/100 | 82/35/8/7/14/100 | 100/0/all kinds 0/0 | 0.13136 | 6.1 |
| 3 | 184/61/12/12/51 | 184/61/12/0/0/100 | 75/36/3/3/13/100 | 100/0/all kinds 0/0 | 0.22098 | 6.4 |
| 4 | 190/60/22/12/50 | 190/60/22/0/0/100 | 95/35/7/2/10/100 | 100/0/all kinds 0/0 | 0.22688 | 6.6 |
| 5 | 243/55/20/17/54 | 243/55/20/0/0/100 | 98/38/7/3/11/100 | 100/0/all kinds 0/0 | 0.24929 | 6.6 |
| 6 | 222/63/16/17/56 | 222/63/16/0/0/100 | 79/31/5/3/16/100 | 100/0/all kinds 0/0 | 0.27080 | 6.1 |
| 7 | 231/63/17/20/55 | 231/63/17/0/0/100 | 111/41/5/5/18/100 | 100/0/all kinds 0/0 | 0.25125 | 8.9 |

Seed 16 night-7 reworded rows (switch_on of 100 TEST; greedy solves of 100): F1 switch_on 100, base 2, adapter 7, X 7. F2 switch_on 100, base 2, adapter 16, X 16. F3 switch_on 100, base 4, adapter 21, X 21. F4 switch_on 100, base 2, adapter 21, X 21.

### Seed 17

| night | S lucky/reached/greedy/lost/gained | X lucky/reached/greedy/lost/gained/on | R lucky/reached/greedy/lost/gained/on | switch test_on/panel_on/by-kind/held_neg_on | kl_S | minutes |
|---|---|---|---|---|---|---|
| 1 | 101/43/9/3/50 | 101/43/9/0/38/188 | 94/38/10/2/21/188 | 100/88/bigger 86, capital 0, count 2, opposite 0, order 0, plural 0/0 | 0.06878 | 9.8 |
| 2 | 138/54/16/10/51 | 138/54/16/0/0/100 | 65/34/6/2/12/100 | 100/0/all kinds 0/0 | 0.12130 | 6.0 |
| 3 | 170/55/14/15/44 | 170/55/14/0/0/100 | 85/32/5/2/13/100 | 100/0/all kinds 0/0 | 0.13236 | 6.3 |
| 4 | 235/62/17/17/45 | 235/62/17/0/0/100 | 109/32/8/4/9/100 | 100/0/all kinds 0/0 | 0.16400 | 6.3 |
| 5 | 186/57/17/21/37 | 186/57/17/0/0/100 | 96/32/7/9/7/100 | 100/0/all kinds 0/0 | 0.19364 | 6.2 |
| 6 | 232/60/15/26/38 | 232/60/15/0/0/100 | 81/32/6/8/8/100 | 100/0/all kinds 0/0 | 0.20839 | 6.2 |
| 7 | 283/56/19/27/49 | 283/56/19/0/0/100 | 133/33/7/8/9/100 | 100/0/all kinds 0/0 | 0.24299 | 8.8 |

Seed 17 night-7 reworded rows (switch_on of 100 TEST; greedy solves of 100): F1 switch_on 100, base 2, adapter 12, X 12. F2 switch_on 100, base 2, adapter 22, X 22. F3 switch_on 100, base 4, adapter 22, X 22. F4 switch_on 100, base 2, adapter 19, X 19.

Reworded frames (GLM's four other candidate wordings, never trained; F1-F4 above): "Using the numbers {NUMS} each exactly once with +, -, *, / and brackets, form {TARGET}, and reply with only the arithmetic expression." / "Using the numbers {NUMS} each exactly once with +, -, *, / and brackets, form an expression equal to {TARGET}, and reply with only that expression." / "Using each of the numbers {NUMS} exactly once with +, -, *, / and brackets, write an arithmetic expression that equals {TARGET}, and reply with only that expression, nothing else." / "Using each of the numbers {NUMS} exactly once with +, -, *, / and brackets, write an expression that equals {TARGET}, and reply with only that expression."

Lost-item counts: S lost 20 items on seed 16 night 7, 27 on seed 17 night 7; lost_items_S_switched_on 0 on all 14 nights (no S-lost panel item ever had the switch on).

## Machine, versions, minutes

- Machine: BensPC (Windows, RTX 5070 Ti). GPU at start: 15745 MiB free of 16303 MiB; compute processes: none (only display/system processes at [N/A]).
- Python: C:/Users/benja/lis300/venv/Scripts/python.exe (the task-named venv; no fallback needed). transformers 5.17.0, torch 2.11.0+cu128, torch.cuda.is_available() True (CUDA 12.8 runtime per the cu128 build tag).
- Model: MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc, present on BensPC; no downloads.
- Minutes in total: script reports 111.3 (nights sum 100.4: seed 16 sum 50.8, seed 17 sum 49.6; pool+base about 10.9). Wall: launched 2026-09-27T03:32:41Z, last night line about 05:23Z, about 111 min. One run, seeds 16 and 17 x 7 nights = 14 nights, no restarts.
- Cost: $0, no rental, one job at a time.

## Every deviation (7 deviations, numbered)

1. Disk gate: ran under the disclosed lowered 3 GB gate. C: free was 4,728,856,576 bytes (4.4 GB) at start, above 3 GB. This is the re-run of job 150, which stopped at 4.4 GB under the old 5 GB gate. C: free later rose to about 6.0 GB during the run (other activity on the PC, not mine).
2. Detached launch: used Task Scheduler (schtasks /create + /run, task "dl9run" pointing at C:\Users\benja\dl9\run_dl9.bat) instead of a shell-backgrounded start, because Win32-OpenSSH kills detached child process trees when the ssh session ends. Verified empirically: two Start-Process launches returned wrapper PIDs 16372 and 11360 but both were gone within a minute with no log output, while the identical command ran fine in the foreground. The python command line and the merged `> gpu/log.txt 2>&1` redirect are the same in effect. Same family as the rsn-358i2/i3 CIM/WMI-detached launches in the ledger.
3. Two failed launch attempts (PIDs above) left no processes and no files; verified gone via tasklist before the successful launch.
4. Helper files live on BensPC only (C:\Users\benja\dl9\run_dl9.ps1, run_dl9.bat, scheduled task "dl9run") plus /tmp files on the Mac: not part of the sealed tree, not copied back, not pushed. A 22-byte mechanism-check file (gpu/mech-test.txt) was deleted on BensPC before copy-back.
5. Projection timing: at 20 min after start no night lines existed yet (pool + base scoring still running), so the projection was made at 04:08 UTC from nights 1-3 (10.1/6.1/6.4 min): about 70 min remaining, finish about 05:25 UTC, inside the 4-hour cap (cap end about 07:26 UTC). No TIME-STOP was needed; the run completed whole.
6. GPU-BUSY.txt pre-existed naming this job (queue job 151-fixsleep-dl9pc-b); per the task that is this job, so the run proceeded and the file was left untouched for the watcher.
7. No code was edited. Selftest printed "dl9 selftest ok". Sealed steps unchanged.

## What it means / doesn't mean (plain high-school English)

- What it means: with number puzzles this distinct from quiz questions, keeping the night's learning in a separate expert and switching it on only for puzzle-shaped questions removed all panel forgetting (X lost 0 of 300 on both seeds, while always-on lost 20 and 27) and kept every bit of the puzzle learning (X gained exactly as much as always-on: +177 and +229 lucky over base 54). Choosing beat chance: the learned switch gained about 3x the random switch (406 vs 136) with fewer losses (0 vs 13).
- What it doesn't mean: this does not show it works for blended or mixed-up questions (these puzzles and quiz questions look very different, so the switch had an easy job), for more than one expert, or for grids. The switch stayed on for all 100 reworded puzzles too, so this run says nothing about what happens when the wording changes more.

## Files for PUSH (no weights saved or pushed)

- artifacts/claude-dl9-20260926/RESULTS-gpu.md (this file)
- artifacts/claude-dl9-20260926/gpu/dl9_results.json (70,687 bytes, rewritten after every seed)
- artifacts/claude-dl9-20260926/gpu/log.txt (17,182 bytes, full run log)
- artifacts/fable-predictions-ledger.md (one appended line)
