# slp-360 results (scrap layer; Fix-sleep thread, 2026-09-25, run 01:00 UTC, CPU, $0)

**Verdict: registered FAIL on P360.6 only, and that failure is an error in my own mark.** P360.6's bar says
"40/40"; the exp-104 world has 50 taught facts, and the sealed scorer checks `taught_good == taught_total == 40`.
All 50/50 taught facts are intact in both seeds. Every other mark passes. P360.5's bar text also says "of 92";
the real count is 75 turns + 6 + 6 = 87, and 87/87 replies are identical (the scorer compares all of them).
I am not editing the sealed marks; a follow-up 360b with the bar fixed is not worth a number (nothing else changes).

| Mark | s1 | s2 |
|---|---|---|
| P360.1 derived rows in main after sleep / after restart | 0 / 0 PASS | 0 / 0 PASS |
| P360.2 main events written during sleep | 0 PASS | 0 PASS |
| P360.3 installed; probes right = twin, ≥ 4/5 | yes; 5/5 = 5/5 PASS | yes; 5/5 = 5/5 PASS |
| P360.4 wrong probe answers, before/after restart | 0 / 0 PASS | 0 / 0 PASS |
| P360.5 replies identical to the twin | 87/87 PASS | 87/87 PASS |
| P360.6 taught facts intact | 50/50, bar misstated as 40 → FAIL as registered | same |
| P360.7 sleep's report row lands in scrap | 1 PASS | 1 PASS |
| P360.8 inferred write from thinking goes to scrap (unit) | PASS | |

Report only (the rule break this fixes): the twin's sleep writes 3 events into the MAIN notebook each night
(a "sleep" entity, a `sleep_report` relation, 1 sleep-derived answering row). With 360: 0 events in main,
3 rows in scrap360/scrap.jsonl.

## Run 1 = VOID (results-run1-VOID.json)
The first run installed nothing in either arm: sleep's learning needs
`artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt`, which is not in git (only on Ben's Mac). The sleeper
then reports `recipe: attempted false, "no base checkpoint"` and still returns `accepted: true`.
I rebuilt the file with the sealed script (`fable_reasoner44.py --stage base --seed 4102`, same script sha
698ecac5...; final loss 0.00012316 vs the logged 0.00012317) and re-ran the same sealed code. Run 2 is the result.

## Finding for 0.1 (SUGGESTED, not shown)
The rent kit (330-rent-kit.md section A) copies only self122_head.pt into the rental tree, and base-seed4102.pt is
not in the 336 SEAL-code list or in git. So in the registered 336 run, sleep most likely never learned anything:
every forced end-of-day sleep would have skipped learning and still reported success. 336 logged no sleep
outcomes, so this cannot be confirmed from its files. 336 stays a registered FAIL either way.
Fix for later rentals: rebuild the file on the box (30 s CPU) as above. Sleep must also stop reporting success
when it did not run (planned inside 364's check, and 361 makes a night rejectable).

Environment for this card test: combined tree (builder-outbox + main), MiniLM from the public hub (same model the
stack pins), self122_head.pt rebuilt with its sealed scripts (sha differs from the Mac file: 7d1e9a... vs 5ca021...;
both arms use the same one, so the comparison is fair, but this is not a byte-exact 0.1).
