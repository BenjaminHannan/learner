# Creative pilot, step (c): numbers after the ladder failed (s100, s101)
Source: creative/results/pilot-s100|s101/pilot.json at commit 8c82c5cad. All DEV (128 puzzles, 32 tries, kept distinct tries). Nothing sealed was read.

## Per rung (best temperature T, chosen by reach@4 among sameness-passing temperatures)
| parent | rung | T | rules share | reach@4 | reach@32 | luck | practice solved /1024 | distinct rule-following | sameness |
|---|---|---|---|---|---|---|---|---|---|
| s100 | 1,500 | 0.21 | 0.291 | 0.160 | 0.508 | 0.047 | 543 | 4.4 | pass |
| s100 | 3,000 | 0.7 | 0.259 | 0.153 | 0.633 | 0.042 | 669 | 5.6 | pass |
| s100 | 6,000 | 0.21 | 0.280 | 0.230 | 0.688 | 0.063 | 692 | 4.1 | pass |
| s100 | 6,000, 16 visits | 2.0 | 0.250 | 0.279 | 0.812 | 0.082 | 861 | 4.1 | pass |
| s101 | 1,500 | 0.21 | 0.285 | 0.161 | 0.516 | 0.046 | 535 | 4.3 | pass |
| s101 | 3,000 | 0.21 | 0.281 | 0.202 | 0.664 | 0.060 | 624 | 4.6 | pass |
| s101 | 6,000 | 0.31 | 0.264 | 0.234 | 0.703 | 0.067 | 763 | 4.0 | pass |
| s101 | 6,000, 16 visits | 2.0 | 0.260 | 0.268 | 0.812 | 0.078 | 850 | 4.1 | pass |

Signal gate (rules share >= 0.50 AND >= 100 practice puzzles solved): practice-solved passes by 5 to 8x on every rung; rules share fails on every rung.

## Shown (from these tables)
- Rules share never exceeds 0.31 at any temperature (0.21 to 3.0) on any rung; the best case is the coldest temperature, 16 visits, sameness-failing (0.304 / 0.310). Temperature is not the cause.
- 4x more three-number warm-up (1,500 -> 6,000) does not move rules share (0.29 -> 0.28, 0.285 -> 0.264); it does move reach@4 (0.16 -> 0.23) and practice solved (543 -> 692).
- Without first-step branching rules share is higher (0.32 to 0.37) but is still < 0.5; branching costs about 4 to 10 points.
- Fallback (a), 16 visits per warm-up record: fit on own warm-up puzzles (greedy accepted, 256 puzzles) rose 0.156 -> 0.609 (s100), 0.156 -> 0.578 (s101); reach@32 0.812 on both, practice solved 861 / 850. Rules share stayed 0.25 / 0.26.
- Fallback (b) (dreams) did NOT run. Code: dreams only run if the parent fits its own warm-up (greedy >= 0.9, a threshold I picked, not in the spec; spec says "fits but fails DEV"). Fit was 0.58 to 0.61, so (b) was skipped, but the final message wrongly says "fallbacks a and b". Not a result bug; the message is wrong.

## Derived (arithmetic on the table, kept-try basis)
- Reach@32 0.81 against the value-blind rule follower's 0.488 pass@32 is above that floor.
- Accepted tries per try (luck) 0.078 to 0.082 with 0.25 to 0.26 of tries following the rules means about 31 to 33% of rule-following tries hit the target, against 2.4% for a value-blind rule follower, about 13x. This is suggested evidence of aim (the explicit aim check, own vs twin target, only runs on a passing warmed parent).

## Untested
- Which rule the other ~75% of tries break on the warmed parent. On the RAW parent (16 DEV puzzles): "op not allowed" 65 to 78% (branch on), "answer is not a written, valid result" 16 to 29%, number-use errors 4%. The warmed parent's mix is unknown because warmed.pt is only saved when a rung passes.
- Whether the 0.50 bar fits this task. It was set as "most tries are rule-following"; the C1 machinery needs accepted tries on enough puzzles, which the model has at 8x the bar.

## What I did not do
Did not change the gate, the temperature rule or the recipe. Added `creative/diagnose.py` (read-only): re-makes the 6,000-rung warmed parent and prints, per temperature with branching on and off, the share of tries following the rules and which rule the rest break. About 40 min of warm-up plus 15 min on a 4-core CPU; no training beyond the same warm-up recipe, DEV only.
```
python3 -m creative.diagnose --ckpt ~/creative/ckpt/B2_s100.pt --data creative/data/c1 \
  --skills-train ~/custom-io/work/data/train.jsonl --warm-to ~/creative/warmed-s100.pt --device cpu > ~/creative/diagnose-s100.json
```
