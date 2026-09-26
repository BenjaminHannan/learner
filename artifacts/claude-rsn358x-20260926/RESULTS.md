# rsn-358x RESULTS (builder, sealed code, 2026-09-26): does maze practice carry over, and more for the loop?

VERDICT: FAIL (X0 met, X1 FAIL, X2 FAIL). PROVED-WRONG clause FIRES: the loop does NOT learn the new kind faster than a same-size plain net with the same practice (loop-pre 4-seed mean steps-to-bar 5000 vs plain-pre 812.5).

Question (sleep research thread): after practising sums, grids and number puzzles, does a net need fewer examples to learn mazes (a kind it never saw), and does the loop need fewer than the plain net of the same size with the same practice?
Answer: practice carries over strongly for the PLAIN net (pre 812.5 mean steps vs fresh 2000, pre < fresh on 4/4 seeds), but not for the loop (pre and fresh both never reach the bar: 5000 on all 4 seeds). The loop learns mazes far SLOWER than plain from either start.

## Marks (PASSMARKS-v2.md, fixed before any run)

| mark | rule | observed | result |
|---|---|---|---|
| X0 validity | plain-fresh reaches bar by 4000 steps on >= 3/4 seeds, AND all 8 source sha256 match | plain-fresh bar on 4/4 seeds (2000 each); sources 8/8 match | PASS (run conclusive) |
| X1 practice carries over (loop) | loop-pre mean steps-to-bar <= 0.75 x loop-fresh mean, AND loop-pre < loop-fresh on >= 3/4 seeds | means 5000 vs 5000 (ratio 1.00, needs <= 0.75); per-seed pre<fresh on 0/4 | FAIL |
| X2 loop faster than plain | loop-pre mean <= 0.75 x plain-pre mean, AND loop-pre < plain-pre on >= 3/4 seeds | means 5000 vs 812.5 (ratio 6.15, needs <= 0.75); per-seed 0/4 | FAIL |
| X3 report | every curve 7x7+9x9, cold, plain-pre vs plain-fresh, 9x9 to100/to200, mean dev counts, test counts all 16 | all reported below; 16/16 evals run exactly once each | done |

PASS = X0 + X1 + X2. This run: X0 PASS, X1 FAIL, X2 FAIL => FAIL, and it stays a FAIL.
Proved-wrong clause ("the loop learns a new kind faster than a same-size plain net with the same practice"): X0 met AND loop-pre mean (5000) at/above plain-pre mean (812.5) => PROVED WRONG.
Not the split case (X1 pass + X2 fail), so the "practice carries over for the loop" sentence does not apply.

## Per-seed steps-to-bar (first check with >= 150/200 on 7x7 dev; 5000 = never by 4000 steps)

| seed | loop-pre | loop-fresh | plain-pre | plain-fresh | X1 seed (loop-pre < loop-fresh) | X2 seed (loop-pre < plain-pre) |
|---|---|---|---|---|---|---|
| 1 | 5000 | 5000 | 750 | 2000 | no (tie) | no |
| 2 | 5000 | 5000 | 750 | 2000 | no (tie) | no |
| 3 | 5000 | 5000 | 1000 | 2000 | no (tie) | no |
| 4 | 5000 | 5000 | 750 | 2000 | no (tie) | no |
| 4-seed mean | 5000 | 5000 | 812.5 | 2000 | 0/4 | 0/4 |

X1 ratio used: 5000 / 5000 = 1.00 (pass needs <= 0.75). X2 ratio used: 5000 / 812.5 = 6.15 (pass needs <= 0.75).
Plain's own carry-over (X3, report-only): plain-pre mean 812.5 vs plain-fresh mean 2000 (ratio 0.41); pre < fresh on 4/4 seeds.

## Steps to 150 (= steps-to-bar) / 200 on 7x7 dev (checks: 0,125,250,500,750,1000,1500,2000,3000,4000)

| net | to-150 | to-200 |
|---|---|---|
| loop-pre-s1 | 5000 | 5000 |
| loop-pre-s2 | 5000 | 5000 |
| loop-pre-s3 | 5000 | 5000 |
| loop-pre-s4 | 5000 | 5000 |
| loop-fresh-s1 | 5000 | 5000 |
| loop-fresh-s2 | 5000 | 5000 |
| loop-fresh-s3 | 5000 | 5000 |
| loop-fresh-s4 | 5000 | 5000 |
| plain-pre-s1 | 750 | 1500 |
| plain-pre-s2 | 750 | 1500 |
| plain-pre-s3 | 1000 | 1500 |
| plain-pre-s4 | 750 | 1500 |
| plain-fresh-s1 | 2000 | 3000 |
| plain-fresh-s2 | 2000 | 3000 |
| plain-fresh-s3 | 2000 | 3000 |
| plain-fresh-s4 | 2000 | 3000 |

Count reaching 200/200 on 7x7 dev by 4000 steps: loop-pre 0/4, loop-fresh 0/4, plain-pre 4/4, plain-fresh 4/4.

## Dev curves (fresh 7x7 / 9x9 dev mazes, 200 each; step 0 = solving cold)

7x7 dev counts by check [0,125,250,500,750,1000,1500,2000,3000,4000]:
- loop-pre-s1: 0,0,3,1,0,3,8,41,51,70
- loop-pre-s2: 0,0,9,2,26,35,17,71,81,100
- loop-pre-s3: 0,0,1,4,17,2,6,9,24,68
- loop-pre-s4: 0,11,0,6,16,16,31,40,71,89
- loop-fresh-s1: 0,0,0,2,13,1,5,8,56,28
- loop-fresh-s2: 0,1,0,0,7,5,6,29,44,68
- loop-fresh-s3: 0,0,0,2,6,21,1,32,21,6
- loop-fresh-s4: 0,0,0,0,3,1,18,18,48,55
- plain-pre-s1: 0,3,29,86,176,199,200,200,200,200
- plain-pre-s2: 0,9,3,87,170,199,200,200,200,200
- plain-pre-s3: 0,0,0,47,39,197,200,200,200,200
- plain-pre-s4: 0,1,25,92,174,195,200,200,200,200
- plain-fresh-s1: 0,0,7,12,40,46,57,153,200,200
- plain-fresh-s2: 0,1,2,16,36,49,131,184,200,200
- plain-fresh-s3: 0,0,3,7,22,57,80,196,200,200
- plain-fresh-s4: 0,0,7,2,7,41,105,164,200,200

9x9 dev counts by check [0,125,250,500,750,1000,1500,2000,3000,4000]:
- loop-pre-s1: 0,0,0,0,0,2,0,7,13,15
- loop-pre-s2: 0,0,3,0,16,11,2,18,10,22
- loop-pre-s3: 0,0,1,0,2,1,1,1,7,16
- loop-pre-s4: 0,3,0,3,12,0,8,10,39,37
- loop-fresh-s1: 0,0,0,0,5,0,4,0,6,1
- loop-fresh-s2: 0,0,0,0,4,1,0,20,8,29
- loop-fresh-s3: 0,0,0,1,4,4,1,16,0,0
- loop-fresh-s4: 0,0,0,0,11,1,17,6,18,10
- plain-pre-s1: 0,0,24,18,24,34,44,44,45,42
- plain-pre-s2: 0,1,0,21,28,31,33,35,28,24
- plain-pre-s3: 0,1,0,6,4,28,23,18,14,6
- plain-pre-s4: 0,0,1,20,34,19,48,42,32,27
- plain-fresh-s1: 0,0,0,6,0,26,22,41,42,38
- plain-fresh-s2: 0,0,0,5,4,11,18,25,47,49
- plain-fresh-s3: 0,0,1,1,3,5,0,22,28,18
- plain-fresh-s4: 0,0,1,1,0,12,13,28,44,44

Solving cold (0-step check): 0/200 on 7x7 AND 0/200 on 9x9 for all 16 nets (no maze knowledge without practice).
Steps to 100/200 on 9x9 dev: 5000 (never) for all 16 nets (best 9x9 dev: plain-fresh-s2 49/200 at 4000 steps).
Mean dev count over the 10 checks (7x7 / 9x9): loop-pre-s1 17.7/3.7, loop-pre-s2 34.1/8.2, loop-pre-s3 13.1/2.9, loop-pre-s4 28.0/11.2, loop-fresh-s1 11.3/1.6, loop-fresh-s2 16.0/6.2, loop-fresh-s3 8.9/2.6, loop-fresh-s4 14.3/6.3, plain-pre-s1 129.3/27.5, plain-pre-s2 126.8/20.1, plain-pre-s3 108.3/10.0, plain-pre-s4 128.7/22.3, plain-fresh-s1 71.5/17.5, plain-fresh-s2 81.9/15.9, plain-fresh-s3 76.5/7.8, plain-fresh-s4 72.6/14.3.

## Sealed test counts (artifacts/claude-rsn358m-20260926/tests, TEST-ONLY, each net evalled exactly once; n = 300 per file)

| net | maze7 | maze9 | maze11 | maze13 |
|---|---|---|---|---|
| loop-pre-s1 | 103 | 35 | 1 | 0 |
| loop-pre-s2 | 134 | 39 | 2 | 0 |
| loop-pre-s3 | 90 | 40 | 0 | 0 |
| loop-pre-s4 | 114 | 59 | 16 | 4 |
| loop-fresh-s1 | 39 | 7 | 0 | 0 |
| loop-fresh-s2 | 92 | 49 | 27 | 9 |
| loop-fresh-s3 | 8 | 0 | 0 | 0 |
| loop-fresh-s4 | 81 | 8 | 0 | 0 |
| plain-pre-s1 | 300 | 64 | 6 | 0 |
| plain-pre-s2 | 300 | 39 | 0 | 0 |
| plain-pre-s3 | 300 | 22 | 0 | 0 |
| plain-pre-s4 | 300 | 43 | 0 | 0 |
| plain-fresh-s1 | 300 | 59 | 7 | 1 |
| plain-fresh-s2 | 300 | 70 | 18 | 1 |
| plain-fresh-s3 | 300 | 30 | 0 | 0 |
| plain-fresh-s4 | 300 | 60 | 9 | 0 |

Test totals right (of 300): every plain net solves all 300 maze7; no loop net tops 134/300 on maze7. (Counts only; no item opened, printed or quoted.)

## Run facts

- GPU: 1x NVIDIA GeForce RTX 5090 (rental 52775569, KR host). torch 2.8.0+cu128 with CUDA, numpy only, no model downloads.
- Code: sealed, from origin/main. SEAL-code-v2.sha256.txt 14/14 OK on the rental before any run. envs selftest prints "selftest ok: ..." (prefix matches), run selftest prints "selftest ok". Code never edited.
- Sources: 8/8 sha256 match (loop/275... sizes 25764244, plain 25573143 bytes).
- Carry: 4000 steps, batch 256, lr 3e-4, 200-step warm-up, same maze stream per seed, arm's own 358i schedule. Plains 8 concurrent (~4.9 min each); loops 2 batches of 4 (~5.4 min each).
- Evals: 16/16 run exactly once per final-carry.pt, counts only.
- Spend: rental 3 ran 16:09:51-16:39:41 UTC = ~0.50 h x $0.4898/h = ~$0.24. Rentals 1-2 never left loading, destroyed, $0. Task total ~$0.24 of $0.60 (sleep research line). Never hit the $0.50 / 1h10m stop. TIME CAP met (all work inside 16:00:02-17:15:02 window).
- Credit at gate: 5.894937036269795 (Director rental gate: none, auto-refill).
- Ben approval: up to $0.60 at 15:50 UTC 09-26 (card cmsg_01FuvegZXjMmeUzStiEFVnEW1ZcuTEwvWrMr3xypKg1TBi, "Approve"). Label claude-sleep-358x. No foreign instance touched; rental destroyed and confirmed gone (0 live labelled claude-sleep-358x).

## Deviations (6)

1. Source path on the Mac has extra nesting: ~/premonition-models/rsn358i/claude-rsn358i-20260926/W/{loop,plain}-sN/final.pt (brief said ~/premonition-models/rsn358i/{loop,plain}-sN/final.pt). Same 8 files, 8/8 hashes match.
2. artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt exists in neither origin/main nor origin/builder-outbox; sources verified 8/8 against the local worktree copy (which matches the grab358i REPORT's 8/8 OK claim on builder-outbox).
3. `claude_rsn358a_envs.py selftest` prints "selftest ok: 1362 four-hands (1062 practice, 300 held out), 1346 three-hands" (required prefix "selftest ok" present, plus detail).
4. Rentals 1 (52774371, offer 46753293) and 2 (52775064, offer 43165145) failed with the host's broken docker-registry proxy (same failure another thread logged for rent-dl6); both destroyed while loading within the 6-min rule, $0. Rental 3 (52775569, KR host, pinned image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime as the running 358t rental uses) worked. 3 rentals total (max allowed).
5. 16-at-once OOMed (each loop proc holds ~4 GB; 16 procs exceeded 32 GB; all 8 loop procs died at step 0, no partial output kept). Kept the 8 surviving plain runs (seeds 1-4, finished 4.9 min), then ran loops in 2 batches of 4 (seeds 1-2, then 3-4) instead of the brief's "seeds 1-2 first" 8-at-once.
6. New SEAL-run.sha256.txt labels weights as W/<R>/final-carry.pt (358i convention); weights never pushed (0 .pt files in the pushed paths; 64 files: 16 runs x carry_log.jsonl + carry_summary.json + tests.json + run log).

## What it means (plain high-school English)

Think of it like learning a brand-new board game after practising card games and number puzzles. The plain-design nets clearly benefited: starting from their puzzle practice they mastered small mazes in ~750-1000 tries instead of ~2000 from scratch. The loop-design nets never got there at all in 4000 tries, with or without their earlier practice -- and they ended far behind plain on the final maze exam too. So for this kind of brand-new challenge, earlier practice helped plain but not the loop, and plain beat the loop outright. What it doesn't mean: this says nothing about the kinds both designs already practised, and nothing about bigger or longer maze training.
