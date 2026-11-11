# English rerun on the real pipeline: results (6 paired seeds, 2026-10-04)

Marks: `PASS-MARKS-R3.md` (committed in 724567c2e before training). Train: the pilot's 48 QA (96 rows). Fresh:
`FRESH-EN-R3.json` (48 new passages, 192 questions, hash-checked on every box). Numbers: `ANALYSIS-R3.json`; rows
in `results/box*/out/`. Fast lane, not a sealed headline test. The fresh set was written by a helper agent; I read
every key once (shown below as caveat).

## Verdict: PASS (shown), but the bar it clears is low

| | fresh exact | "contains" | new-word answers | yes/no | train fit |
|---|---|---|---|---|---|
| pool (today's exit) | 4.3% | 5.0% | 0.0% | 37.9% | 100% |
| allptr (all words + pointer) | 34.7% | 42.8% | 33.0% | 47.0% | 100% |
| frozen 1.2B LM alone, chat prompt, 1 run | 29.7% | 76.0% | 34.8% | 0.0%* | 25%* |

- allptr - pool, all 192: **+30.4 points, CI +12.7 to +48.0**; per seed 18, 64, 24, 20, 27, 30. Mark was +25. PASS.
- New-word answers: +33.0 (CI +13.6 to +52.5). Today's exit gets every one of them wrong (0 of 984 across seeds).
- Zeroing the core's 8 vectors drops allptr to 0.0% (contains 1.7%).
- *lm_alone answers in sentences ("Dax tossed the plum."), so exact match undercounts it; "contains" 76% is the
  fairer view of what the bare LM can read. Its yes/no answers come as "No, Rho didn't give it." (0% exact).

## What this means (suggested)
- The exit fix works on English too: new words now come out (0% -> 33%).
- But with only 48 training questions both arms fit 100% of training and the trained system is only at the bare
  LM's exact-match level, far below what the LM can read (76% contains). Seeds vary hugely (21% to 68%); weak seeds
  emit garbled copies ("Ticket clashed", "Loyalty"). That is the explanation-B signature: too little data, not the door.
- Next single change: train the same allptr setup on many generated English rows from the same six families
  (the skills-curriculum route), same fresh set, same marks shape.

## Caveats
- One seed of lm_alone (it is deterministic). The fresh set is ours, 8 passages per family, unreviewed by a second
  reader. 2000 updates; no auxiliary rows (the PC pilot had 24).

## Cost
About $1.12 on vast across 6 boxes (`LEDGER.md`); credit $5.19 at 03:46 UTC.
