# rsn-356 results (builder): one-fact twins, paired vs unpaired — registered verdict FAIL

Verdict first: **FAIL**. T1 fails on both seeds (fresh panel296: paired −4 and +4 vs unpaired, bar ≥ +6)
and T2 fails on both seeds (held-out change pairs both-right: paired +2 and −6 vs unpaired, bar ≥ +30).
T3 passes everywhere (0 checked inventions on every checkpoint and panel). PASS needed T1, T2 and T3 on
both seeds. The **"proved wrong" clause TRIGGERED**: T2 is within ±12 of unpaired on both seeds (+2 seed 1,
−6 seed 2), i.e. pairing the twin next to its original did not make the model read the deciding fact.

Design: design/v3/30-modes/356-one-fact-twins.md. One change from rsn-296's plain arm in TRAINING only:
after each practice puzzle with a clean "delete" twin, the next puzzle is its own twin (paired arm) or the
twin of a different thrown-away puzzle (unpaired control, same mix). Base 296, not 355. Seeds 1–2, plain arm,
6000 copy + 6000 practice steps, batches/LR/reward/fact-check/eval identical to 296. Sleep-thread code sealed
and unpatched; all code/panel seals verified OK from a clean `git archive origin/main` before training
(SEAL-code 8/8, panel296-v2 2/2, panel294-v3 2/2) and both selftests printed "selftest ok" on BensPC
(`claude_rsn296_gen.py`: gold-action mismatches 0; `claude_rsn356_twins.py`).

## Training (4 runs, 2 at a time, --workers 0, BensPC RTX 5070 Ti, torch 2.11.0+cu128, $0)

Pilot (paired, seed 9, 100 copy + 50 practice steps): 0.6 min total (copy 0.30 min, practice 0.23 min) →
full-run estimate 60×0.30 + 120×0.23 ≈ 46 min/run, 4-run total ≈ 3.0 h wall, under the 9 h gate.
2-at-a-time chosen on rsn-355's evidence (its two finals share identical timestamps, i.e. it ran paired).

| run | minutes | copy loss first → last (action_ce) | practice reward mean per 1,000 steps |
|---|---|---|---|
| paired-s1 | 59.8 | 3.8787 → 0.0105 | 0–999: 0.7459; 1k: 0.8038; 2k: 0.8472; 3k: 0.8653; 4k: 0.8632; 5k: 0.8623 |
| unpaired-s1 | 62.7 | 3.8747 → 0.0046 | 0–999: 0.7090; 1k: 0.7702; 2k: 0.8069; 3k: 0.8283; 4k: 0.8890; 5k: 0.8461 |
| paired-s2 | 59.7 | 3.7855 → 0.0051 | 0–999: 0.7376; 1k: 0.7794; 2k: 0.7654; 3k: 0.8233; 4k: 0.8501; 5k: 0.8659 |
| unpaired-s2 | 62.5 | 3.7518 → 0.0312 | 0–999: 0.7209; 1k: 0.7617; 2k: 0.8068; 3k: 0.8560; 4k: 0.8660; 5k: 0.8877 |

Copy learned fully on all 4 runs (last action_ce ≤ 0.04). Seed-1 pair ran first, then seed-2 pair.

## Panel totals (checked_right; each of the 8 checkpoints evaluated exactly once)

Fresh panel296 v2 (298 items):

| run | copy-only (raw / checked) | final (raw / checked) |
|---|---|---|
| paired-s1 | 173 / 176 | 226 / 231 |
| unpaired-s1 | 177 / 178 | 231 / 235 |
| paired-s2 | 170 / 175 | 226 / 231 |
| unpaired-s2 | 174 / 179 | 223 / 227 |

Transfer panel294 v3 (300 items):

| run | copy-only (raw / checked) | final (raw / checked) |
|---|---|---|
| paired-s1 | 205 / 205 | 257 / 257 |
| unpaired-s1 | 205 / 203 | 254 / 254 |
| paired-s2 | 204 / 204 | 255 / 255 |
| unpaired-s2 | 206 / 205 | 254 / 254 |

Final-checkpoint category detail, fresh panel296 (checked_right / n):
- paired-s1: backwards 30/30, before_after 21/30, comparing 16/30, counting 24/30, heldout_three_step 0/30,
  missing_fact 30/30, newest_correction 20/28, one_step 30/30, two_step 30/30, yes_no 30/30 (total 231).
- unpaired-s1: backwards 30/30, before_after 23/30, comparing 16/30, counting 25/30, heldout_three_step 0/30,
  missing_fact 30/30, newest_correction 21/28, one_step 30/30, two_step 30/30, yes_no 30/30 (total 235).
- paired-s2: backwards 30/30, before_after 21/30, comparing 16/30, counting 25/30, heldout_three_step 0/30,
  missing_fact 30/30, newest_correction 19/28, one_step 30/30, two_step 30/30, yes_no 30/30 (total 231).
- unpaired-s2: backwards 30/30, before_after 18/30, comparing 16/30, counting 25/30, heldout_three_step 0/30,
  missing_fact 30/30, newest_correction 18/28, one_step 30/30, two_step 30/30, yes_no 30/30 (total 227).
- Copy-only finals for reference: all four 175–179 (comparing 0/30, counting 0/30, before_after 6–11/30).

Final-checkpoint category detail, transfer panel294 (checked_right / n):
- paired-s1 (257): backwards 30/30, before_after 20/30, comparing 12/30, counting 30/30,
  heldout_big_notebook 15/15, heldout_three_step 0/15, missing_fact 30/30, newest_correction 30/30,
  one_step 30/30, two_step 30/30, yes_no 30/30.
- unpaired-s1 (254): same except before_after 18/30, counting 29/30 (rest identical, incl. comparing 12/30).
- paired-s2 (255): before_after 19/30, counting 29/30, comparing 12/30 (rest 30/30 or 15/15, three-step 0/15).
- unpaired-s2 (254): before_after 17/30, counting 30/30, comparing 12/30 (rest identical).
- Copy-only: all four 203–205 (comparing 0/30, counting 0/30, three-step 0/15).

Held-out change pairs (600, both answers right after the fact-check):

| run | copy-only both_right (base / twin) | final both_right (base / twin) |
|---|---|---|
| paired-s1 | 398 (398 / 399) | 455 (530 / 502) |
| unpaired-s1 | 392 (397 / 395) | 453 (529 / 500) |
| paired-s2 | 391 (393 / 397) | 449 (531 / 498) |
| unpaired-s2 | 394 (398 / 395) | 455 (534 / 501) |

Final per-category both_right / 100 (paired-s1, unpaired-s1, paired-s2, unpaired-s2):
value1 100/100/100/100; value2 99/100/100/100; yesno 100/100/100/99;
compare 0/0/0/0; count 56/54/51/57; correction 100/99/98/99.
Compare twins are never both right (twin flips the winner and the model keeps the old answer);
value/yesno/correction twins are at ceiling in both arms, so T2 could only move on count — and didn't.

## Marks (final checkpoints, integer counts)

| mark | bar | seed 1 | seed 2 |
|---|---|---|---|
| T1 fresh panel296 total, paired vs unpaired | paired ≥ unpaired + 6 | 231 vs 235 (−4) **FAIL** | 231 vs 227 (+4) **FAIL** |
| T2 change pairs both_right, paired vs unpaired | paired ≥ unpaired + 30 | 455 vs 453 (+2) **FAIL** | 449 vs 455 (−6) **FAIL** |
| T3 invented answers (checked), each panel, both arms | ≤ 2 | 296: 0/0 copy+final both arms; 294: 0/0 copy+final both arms **PASS** | same, all 0 **PASS** |
| T4 vs 296 plain (fresh 225 / 217; transfer 238 / 238), per category | report | fresh paired 231 (+6), unpaired 235 (+10); transfer paired 257 (+19), unpaired 254 (+16) | fresh paired 231 (+14), unpaired 227 (+10); transfer paired 255 (+17), unpaired 254 (+16) |

T3 detail: checked_answered_without_fact is 0 on all 8 panel296 checkpoints (raw 5 each, all fact-checked to
"I don't know") and 0 on all 8 panel294 checkpoints (no standing invented answers). matches the prediction.
T4 detail: both 356 arms beat the same-seed 296 plain totals on both panels (fresh +6/+10 s1, +14/+10 s2;
transfer +16…+19), but the paired−unpaired gaps that would show a pairing effect are −4/+4 fresh and +2/−6
pairs — noise around zero. Per-category, 356 finals vs 296 plain finals: counting jumped (24–25/30 vs 12/30
fresh; 29–30/30 vs 12–13/30 transfer) in BOTH arms, comparing is flat (16/30 fresh, 12/30 transfer, same as
296), three-step still 0 everywhere. So the extra twin puzzles shifted counting in both arms equally; pairing
added nothing. "Proved wrong" clause: T2 within ±12 of unpaired on both seeds (+2, −6) → **triggered**.

## Checkpoints (kept on BensPC only, never pushed)

C:/Users/benja/premonition-models/rsn356/paired-s1, unpaired-s1, paired-s2, unpaired-s2
(copy_only.pt + final.pt per run; moved there after evals; sha256 re-verified after the move, all match
SEAL-run.sha256.txt):

| file | sha256 |
|---|---|
| paired-s1/copy_only.pt | 2adb3851a5da0bccea2a546750c9c6a20fd4fab0b60f3ccfe1f2c44b8dcc16ff |
| paired-s1/final.pt | d556e56e44c538f104bdc1716ef99791091f05401ed2d8911138c8e95d236772 |
| unpaired-s1/copy_only.pt | d169cdf1d157752bccd45b6cbaf4971b18b88605332cf781d81c3ca05e1ad040 |
| unpaired-s1/final.pt | 2c58c4e5eaf65de6466fd1c7bb3699240c63950f9c13bc8acb92decb5f139a0d |
| paired-s2/copy_only.pt | f12a6296614bae83057b3fd490e1a784bcb1e7b4d7241a6440a70b3e9e65d6e0 |
| paired-s2/final.pt | 3a00213dd15b3cdabae4e83a387465be71cad61c43d9614786daf7045bd41920 |
| unpaired-s2/copy_only.pt | 3dd046752e4c7c6641a2b4ec25848a9973951919149d64797832563ded2679e8 |
| unpaired-s2/final.pt | 236c1887b84052d1394a67a7ecd11767a35819343d303d46bc52b4c2fd0d8235 |

## Deviations (all reported; code never patched, panels never read)

1. OPUS-RULES.txt path from the brief does not exist (that scratchpad dir is empty); worked from the brief's
   own rule summary instead (additive-only, ledger append-only, seals, GPU rules, counts).
2. --workers 0 on all BensPC runs (Windows deviation, as the mode doc prescribes).
3. 2-at-a-time training (seed-1 pair, then seed-2 pair) on rsn-355's evidence; pilot gate computed exactly as
   specified (60× copy-phase + 120× practice-phase ≈ 46 min/run, ≈ 3.0 h total, under 9 h).
4. rsn-355 judged finished from its two final.pt files present + idle GPU + no python process (could not
   coordinate directly; one-GPU-job-at-a-time kept throughout — GPU was idle at every launch).
5. Eval JSONs (train logs/summaries, dev, panel, pairs) copied back to runs/<R>/ on the Mac; weights never
   copied to the Mac and never pushed.

## What it means (plain high-school English)

Showing the model each puzzle next to its one-fact twin did not teach it to read the deciding fact. On the
fresh blind test the paired and unpaired models scored 231 vs 235 and 231 vs 227 — basically tied, far from
the +6 needed. On the special twin test both got about 450 of 600 pairs fully right, again tied. The twin
puzzles did change something — both groups got much better at counting than last night's model — but the
control group got the same boost, so it came from seeing extra puzzle types, not from pairing. Neither group
ever invents answers after the fact-check (0 times, limit 2).

## What it doesn't mean

It doesn't mean twins are useless data — both arms beat the 296 baseline on counting and overall. It doesn't
mean the model learned to compare numbers or multi-step chains — comparing is flat at 16/30, three-step still
zero. It doesn't mean pairing would work with a different setup — this test only covers side-by-side twins in
the same batch on the plain arm.
