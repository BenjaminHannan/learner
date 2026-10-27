# rsn-294 results (builder, third try, 2026-09-23/24 UTC)

**Verdict: FAIL.** The brain-style loop reasoner trained end to end on both seeds, and the
fact-check plus honest "I don't know" marks pass, but the loop scores far below the code arm
overall (P294.2), loses to the equal-size plain transformer on the held-out set (P294.4),
regresses on the copy-phase categories (P294.5), and practice teaches almost nothing on seed 2
(P294.6: +4, bar +10). What proves the loop idea wrong per PASSMARKS (P294.4 fails) happened on
both seeds: a plain model of the same size reasons over the notebook as well as, or better
than, the loop. What proves practice wrong (P294.6 fails) happened on seed 2 only; seed 1
passed with +47.

Plan: design/v3/30-modes/294-learned-reasoner-plan.md (on origin/main).
Code sealed in SEAL-code-v2.sha256.txt (7/7 lines OK on the GPU host before training).
Panel: artifacts/claude-reasonpanel294-20260923/items-v3.jsonl, 300 items, run exactly once per
checkpoint (8 checkpoints x dev + eval = 16 evals, 0 failures); outputs below are
category-level counts only. Panel items were never opened, printed, or tuned on.
Train: defaults (copy 6000 steps batch 256, practice 6000 steps batch 128 x 8 tries, lr 3e-4,
--workers 4), 4 runs, 2 at a time on 1 x RTX 5090 (contract 52300816, offer 43165154, 32 cores,
rel 0.9951, $0.4727/h). New venv: torch 2.14.0+cu130, CUDA True, numpy 2.4.6.
Params: loop 30771221, plain 30938261 (match PASSMARKS).

## Per-run training + panel totals (checked = after fact-check; n = 300)

| run | min | copy loss first -> last | practice reward first -> last | panel copy-only (right/idk/wrong) | panel final (right/idk/wrong) |
|---|---|---|---|---|---|
| loop-s1 | 40.4 | 4.0318 -> 1.0745 | 0.2458 -> 0.3286 | 45 / 238 / 17 | 92 / 154 / 54 |
| plain-s1 | 30.3 | 3.9513 -> 0.0016 | 0.7603 -> 1.0070 | 165 / 121 / 14 | 184 / 62 / 54 |
| loop-s2 | 40.5 | 4.0276 -> 0.1215 | 0.6483 -> 0.9040 | 107 / 169 / 24 | 111 / 147 / 42 |
| plain-s2 | 29.9 | 3.9393 -> 0.0003 | 0.7560 -> 1.0199 | 156 / 127 / 17 | 189 / 48 / 63 |

Raw "answered without a fact" (answer given when gold is UNKNOWN; all inside missing_fact):
loop-s1 copy 22, loop-s1 final 22; loop-s2 copy 8, loop-s2 final 4; plain-s2 copy 2, final 1;
plain-s1 0. After the fact-check, checked answered-without-fact is 0/300 for every loop
checkpoint (missing_fact checked_right = 30/30 throughout).

## Marks (code arm: 210/300 checked-right overall; per-category code: one_step 30, backwards 30, yes_no 30, newest_correction 30, missing_fact 30, all /30)

| mark | bar | loop seed 1 | loop seed 2 |
|---|---|---|---|
| P294.1 invented (checked answered w/o fact) | <= 2/300 | 0/300 PASS (raw 22, all fact-checked to IDK) | 0/300 PASS (raw 4, all fact-checked to IDK) |
| P294.2 loop right overall | >= code+30 = 240/300 | 92/300 FAIL | 111/300 FAIL |
| P294.3 missing_fact honest IDK | >= 25/30 | 30/30 PASS | 30/30 PASS |
| P294.4 held-out loop minus plain (three-step 0/15 + big-notebook 0/15 vs s1 plain 0/15 + 5/15; s2 loop 0/15 + 1/15 vs plain 0/15 + 8/15) | >= +10 | 0 - 5 = -5 FAIL | 1 - 8 = -7 FAIL |
| P294.5 no regression (one_step / backwards / yes_no / newest_correction, each >= code-3 = 27/30) | >= 27 each | 3 / 7 / 11 / 12 FAIL all four | 19 / 8 / 23 / 12 FAIL all four |
| P294.6 practice teaches (final minus copy-only overall right) | >= +10 | 92 - 45 = +47 PASS | 111 - 107 = +4 FAIL |

Detail for P294.5 (loop final checked_right /30): seed 1 one_step 3, backwards 7, yes_no 11,
newest_correction 12; seed 2 one_step 19, backwards 8, yes_no 23, newest_correction 12.
For reference, plain finals: seed 1 one_step 30, backwards 28, yes_no 29, newest_correction 20;
seed 2 one_step 27, backwards 29, yes_no 25, newest_correction 30.
Loop finals elsewhere (seed 1 / seed 2 checked_right): counting 0/0, comparing 12/12,
before_after 11/5, two_step 6/1.

## Spend

Contract 52300816 alive 2026-09-23 21:24:39Z to 2026-09-24 00:12:37Z = ~2.80 h x $0.4727/h
= ~$1.32 (ceiling $4/3 h respected on dollars; wall-clock over 3 h only because ~1 GB of
checkpoint download ran at ~100-400 KB/s). Credit was $9.31 at rental, floor $4 untouched.
Instance destroyed at end; 0 instances live after. Pilot (timing only, seed 9, 100 copy + 50
practice steps): loop copy 0.22 min + practice net 0.19 min; plain copy 0.14 min + practice
net 0.13 min; full-run estimate 60x/120x rule = 36 + 24 = ~60 min per pair, ~120 min for all
four, under the 150 min cap, so full training proceeded.

## Checkpoints (kept at ~/premonition-models/rsn294/<run>/, never pushed; sha256 match SEAL-run.sha256.txt)

- loop-s1/copy_only.pt 7ff5c8e8756595531f07e1808a6ff072f498a61813a4044bc8582f1bceda8d64
- loop-s1/final.pt efcde28797f39ee1d7240b0508c4697b58629c330ac9d41848e157ae5585cf1f
- plain-s1/copy_only.pt 8dcd62c6e7ad5258b91a2ad294f74ecb6f16b6483639e4d955eeb5d24926aa69
- plain-s1/final.pt 06be1050738439c03e3ed08f24585e552108e8832d16f886e581506da5929a5b
- loop-s2/copy_only.pt c8faa042e5640bf564e33463cb68de7e707efeb119e4a9fa1063f6c1022fcffd
- loop-s2/final.pt 1377ebe783ee86ccd6c9b160d0d915f7619c86abb98bf1c498cd2beb72e7e0ad
- plain-s2/copy_only.pt dbafebed78c9af671fe65647510a7ea565aa67be68a4bfc964eb9ec0a55f9fc4
- plain-s2/final.pt fbef3926fd12ff5873e53df12cde5c9ad7a3fc142cfb0502a51f5bd16c071310

Deviations: (1) OPUS-RULES.txt path from the task does not exist (empty scratchpad dirs);
worked from the rules restated in the task. (2) Tarball-of-main via git archive + scp instead
of git clone (explicitly allowed). (3) Venv got pip's latest torch 2.14.0+cu130 + numpy 2.4.6
(task requires only a CUDA torch + numpy). (4) First plain pilot launch failed (wrong remote
cwd) and was restarted from the repo root; timing-only, no side effects. (5) `cd ... && ...
&` shell backgrounding dropped the cwd once more on the remote; restarted correctly, no
double-run of any eval (16 eval outputs, one per checkpoint per kind). (6) Checkpoint download
used per-run subdirs under ~/premonition-models/rsn294/ (flat names would have collided).
Panel items read by me: 0. Sealed files edited: 0. Code patched: never.
