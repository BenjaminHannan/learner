# RESULTS — Exp 118b: train-list leftover brake on the sealed ears-rung-2 checkpoints

**Result: the training-derived list keeps the ears SAFE (0 silent wrong writes,
all seeds, both "aside" traps now ECHO) and recovers SEEN execution to within
the bar (455→413, −9.2%, PASS) but NEW still fails it (640→510, −20.3%, FAIL).
Safety PASS, coverage SPLIT — the gap is now three named word classes, not the
whole framing vocabulary.**

## 1. What ran

Single-change follow-up to exp 118 per the brief: 118's CAL-tuned V2 (11 words)
replaced by TRAIN_FRAMING_V2 (2,618 words, K=50, J=0.01, fixed on CAL only;
`fable_brake118b_wordlist.txt`, sha256 `60a4450e…f3743ad8cb`). Pool identity
gate reproduces the BensPC training pool exactly (kept=140,903 dropped=614).
V1 and the relation cue-word rule are byte-identical imports from 118. Sealed
PASSMARKS (hash `a412d978…`) + ledger P118b.1–P118b.5 before scoring. All
sealed panels rescored from cached exp-95 rows at the sealed taus; reading94
ran the sealed checkpoints on Mac CPU. Registered run 113.8 s. Cache check:
SEEN STATE 817 = 163 OPEN-gold + 654 concrete (doc-95 integers reproduced).

## 2. Marks (with brake; exp-47 sealed numbers in brackets)

| mark | ensemble | 4701 | 4702 | 4703 | verdict |
|---|---|---|---|---|---|
| B1 SAFE silent /6,500 (trap) | 0 | 0 | 0 | 0 | **PASS** |
| B2 NEG exec-as-fact /2,092 | 0 (0) | 0 | 0 | 0 | PASS |
| B2 ASK wrong exec | 0 (0) | 0 | 0 | 0 | PASS |
| B2 NEWREL wrong-seen /1,500 | 0 (0) | 0 | 0 | 0 | PASS |
| B3 SEEN stmt-exec (old 455/83/527/100) | 413 | 73 | 482 | 82 | **PASS ens** (−9.2%; singles −12.0/−8.5/−18.0%) |
| B3 NEW stmt-exec (old 640/102/766/103) | 510 | 91 | 602 | 76 | **FAIL ens** (−20.3%; singles −10.8/−21.4/−26.2%) |
| B4 time | 113.8 s | — | — | — | **PASS** (< 600 s) |
| reading94 writes/right/wrong | — | 0/0/0 | 0/0/0 | 0/0/0 | vacuous (brake = nobrake = 0, matches 106) |

Correct counts bit-identical to exp 47 everywhere (SEEN 1,954, NEW 2,682 —
downgrades became correct ECHOs). Trap #259/#751 both fire (`aside` leftover)
and ECHO; `aside` never entered the list (asserted in code). t_seen fires 42,
t_new fires 130 (118: 264 + 561).

## 3. Why NEW still fails (firing analysis, every remaining class)

Test introducers 118 named are now covered ("write this down", "just so you
know", "at the moment", "Small update", "Remember that" all pass). Four
downgrade classes remain, each with a training-data mechanism: (1) **"new"**
(t_seen 16, t_new 90: "New fact:" draws) — excluded by the J-filter because
"new" sits inside gold VALUE spans in 1,242/6,701 = 18.5% of training
occurrences; it is genuinely both framing and content. (2) **"one"** (15/17:
"One thing:/Quick one:") — same mechanism, 384/5,344 = 7.2% value
contamination. (3) **"days"** (0/28: "these days") — temporal framing absent
from the training draw AND value-contaminated (20/442 = 4.5%). (4) **double
mention** (11 SEEN: "about NAME: NAME is …") — the frame covers one mention;
the "about"-phrase name is a true leftover, a span-coverage gap rather than a
vocabulary gap. List diff vs 118's V2 (`fable_brake118b_listdiff.json`):
+2,609 words, −2 (`mind`: 31 training occurrences < K=50; `one`: J-filter).

## 4. What it means / what it does not mean

What it means: deriving the list from the training pool (not the CAL draw)
recovers most execution while holding safety at zero — and the residual cost
is fully explained by three words the J-filter provably must exclude plus one
span-coverage pattern. Framing lists generalise exactly as far as the
training distribution's framing vocabulary reaches.

What it does not mean: it does not mean the coverage problem is solved (NEW
misses by 66 executes; "New fact" draws dominate t_new), or that a bigger
list would be safe (every K≤30 list contains "aside"), or that WebRED moved
(ensemble executes 0 on wpos/wclosed/wnewrel).

Deviations: none from the sealed plan. Ledger P118b: TRUE, TRUE, FALSE, TRUE,
TRUE(vacuous). Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_brake118b_score.py --out
artifacts/fable-brake118b-20260922/fable_brake118b_results.json`.
Questions for Ben: none.
