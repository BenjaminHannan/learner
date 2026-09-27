# Number-puzzle diagnosis (Step 1, pre-registration)

## Brain first
SUGGESTED human analogy, not a neuroscience finding: people often choose a pair, compute an intermediate result, test a target relationship such as 3 × 8, and try another pairing when that branch fails. BRAIN-FIRST.md was written before choosing a candidate.

## What the code and code-generated data show
SHOWN: the source has 1,346 three-number hand/target pairs and 1,062 four-number practice hands. The old 300 held-out four-number hands exhaust the remaining solvable hands in the 1–13, target-24 domain. The baseline training stream samples this finite set repeatedly, with input-number permutations but a fixed stored solution.

SHOWN: the token loss and halt target use exact agreement with the stored postfix expression. The checker accepts any expression that uses exactly the supplied numbers and evaluates to the target. The code-only exhaustive postfix audit finds alternatives on 2,333 / 2,408 practice pairs (96.9%; median 8 valid expressions, range 1–335). Every enumerated label was checked by the existing exact checker; every stored solution was found in its set. This proves a supervision mismatch, not its causal contribution to poor transfer.

SHOWN: on a deterministic 12-pair sample, replacing one token in a valid answer with a token from a different valid answer made an invalid answer for all 12 pairs. Training on independent unions of allowed tokens would therefore be incorrect. The relevant unit is a whole expression.

SHOWN from our own read-only recount of historical raw files at builder-outbox commit 43b4d6f487f3ac67cc4deaf4c889e28b2416d0a0: all eight kind-labelled runs report final-window training exactness 1.0 on numbers3/4. Held-out loop numbers4 counts are 2,5,1,0; plain counts are 1,1,2,1; numbers5 is 0 throughout; sums4 is 300 throughout and grids5 is 298–300. The training values are rounded log-window means, not an exhaustive census of every practice hand. This is strong evidence of a memorization/generalization gap in that recipe. Script: codex_numbers_20260927_history.py; local data: diagnostics/historical-recount.json. Our own fixed-env baseline result follows below when finished.

SHOWN: the loop has recurrent hidden state and can change answers over rounds. It does not explicitly maintain a stack of arithmetic branches and receives only final-answer loss. UNTESTED: whether its hidden state implements backtracking. The claim that it has no possible way to try alternatives would be too strong.

SHOWN: original tensorization uses the first item's hidden kind, and the embedding adds it to each token. The new runner emits zero for every item's env without reading its kind. Two unused env rows are retained and counted as parameters. The CPU 48-round poison check passed. This common repair is required for both experimental arms.

SUGGESTED causes: finite-pool repetition permits memorization; one-answer loss encourages copying a solver's arbitrary expression style; exact-answer halt targets can discourage alternative valid answers; final-answer-only supervision supplies no direct evidence about useful intermediate operations. None is individually established as the cause of the historical generalization gap.

## Local diagnostic baseline
SHOWN: completed fresh diagnostic seed 9276191, M3 Pro, torch 2.11.0, MPS float32, 2 layers × width128, 8 heads, 430,238 parameters including 256 unused env parameters; 20,000 steps, batch128, original three-kind stream/20,000 Latin pool, lr3e-4/warmup1000, 16 total training rounds/6 graded/48 evaluation rounds, original v2 own-stop. Training took 14.16 minutes. At the model's own v2 stop: practice numbers3 508/1,346 valid (494 stored-exact); practice numbers4 46/1,062 valid (44 stored-exact); design numbers4 2/300 valid (1 stored-exact); sums4 298/300; grids5 248/300. The final training window numbers4 exactness is 8.04%, and evaluation uses a different random-round regime (48 rounds/own stop), explaining why its rate is not identical. All tested hidden-kind poison variants produced identical logits and raw halts. No sealed five-number panel has been created or scored.

SHOWN: this smaller, shorter fixed-env baseline underfits number practice. It does NOT reproduce the historical perfect-training/near-zero-transfer pattern, so it cannot yet establish that the same memorization mechanism survives the fixed-env repair and capacity reduction. The original eight-run gap is independently verified; local reproduction remains UNTESTED at an adequately fitted setting. A registered comparison should not present this diagnostic as proof that a proposed change fails to generalize.

SHOWN error breakdown on the disclosed numbers4 design panel: 142 wrong input-number multisets, 100 malformed postfix expressions, 54 wrong arithmetic results, 2 invalid tokens, 2 valid answers. Categories are exclusive in the checker's diagnostic ordering. Only 6/300 have a valid answer at any of 48 rounds; all 300 finish at the fallback round 48. Changing only when it stops cannot make this checkpoint solve more than 6/300 of these fixed trajectories. SUGGESTED: the observed failure is mainly answer construction/arithmetic learning, not merely choosing the wrong stopping round.

## What a single change could test
The initial diagnosis considered whole-expression validity-aware supervision. The revised request prioritizes Ben's learned scratch-card store, and Ben subsequently selected scratchpad-only after comparing it with partial bookmarks. The answer-target mismatch remains a diagnostic finding, not part of this candidate. The candidate preserves the original answer and halt losses, source stream, and core settings.

## Temporary memory and current decision

SHOWN: the puzzle loop retains hidden vectors but is separate from the broader card-store implementation. It has no explicit scratch-card or branch-snapshot interface. See diagnostics/WORKING-MEMORY-NOTE.md for the inspected sources and the distinction Ben raised during brainstorming. UNTESTED: whether adding explicit writable workspace helps. Ben has now selected scratchpad-only; no candidate has been implemented, registered, or trained at this diagnosis commit. This report makes no claim about the 1B model or joined build.

## Adequately fitted local baseline — interim evidence before Step 2

SHOWN: the revised fixed-env diagnostic (seed 9276193, width256, 2 layers, batch128, MPS float32, original mixed kinds) excludes 100 of the original 1,062 four-number practice hands as its own development set. Its exhaustive own-stop probe at step20,000 scores 919/962 practice hands exactly (95.53%), clearing the user's 0.95 prerequisite, and 0/100 development hands. At step25,000 it scores 933/962 practice exactly (96.99%), still 0/100 development, with fresh dev sums4 200/200 and grids5 197/200. These are actual counts, not rounded training-window means. The full 60,000-step diagnostic remains running; no final run result is asserted here.

The step25,000 checkpoint and probe were preserved in diagnostics/fit-gate-step25000/checkpoint.pt and evidence.json. The checkpoint SHA256 is c15df69d2c78184f4930e2adbcf2c31b9aea748b409611c71451cb3770927ecd. The run's manifest records disjoint 962/100 practice/development sets and hashes of their exact panels. Code provenance is preserved by diagnostics/fit-baseline-runner-snapshot.py. No original registered test panel was scored for this revised diagnosis.

SHOWN: this adequately fitted fixed-env smaller baseline reproduces a substantial memorization/generalization gap on our own development split. SUGGESTED: adding an explicit learned scratch workspace is now a relevant single-change test of whether saved intermediate features help transfer. This does not establish why the baseline memorizes, or that explicit cards will fix it.

The prerequisite has been observed before candidate implementation. The registered supervisor will additionally require the completed diagnostic's final summary/checkpoint to meet the same criterion before any registered training starts. SELECTED-DESIGN.md specifies the scratchpad-only candidate; required test-time wiping must remove keys and values before every read. All selection remains learned and no inference solver or intermediate card labels are introduced.
