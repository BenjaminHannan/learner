# RESULTS — exp 102: patch the 15 remaining redteam98 bugs (2026-09-22)

Result first: Loop102 (Loop96 + five additive fixes in
`scripts/fable_loop102_agent.py`) clears all 16 redteam98 reproducers (before:
Loop96 H5 OK + 15 BUG), flips all 64 sealed cases with 0 OK->BUG, keeps every
loop96 regression mark green, and refuses none of 30 innocent sentences.
P1-P4 all PASS; whole wave ~1 min on Mac CPU, offline.

## Integer table (every seed/case reported, never averaged)

| mark | bar | observed |
|---|---|---|
| P1 | 16/16 reproducers OK after (before = Loop96) | 16/16 OK; before H5 OK + 15 BUG |
| P2 | 0 OK->BUG over 64 sealed cases | 0 OK->BUG; 16 BUG->OK; 0 still BUG |
| P3-L1 | 2/2 clarify, 0 FACT/ENTITY (loop90 before writes) | PASS (before 2 writes) |
| P3-L2 | 74 RT81 cases, 0 wrong writes | PASS; changed vs loop90: 6 ids |
| P3-L3 | 3/3 fix77 patterns | PASS (R1/R2/R3) |
| P3-L4 | RT79-18/09/53 OK, 1 site each, web-verified=0 | PASS |
| P3-L5Z1 | 60/60 turns, 0 wrong | PASS |
| P3-L5Z2 | 200/200, 0 WRONG | PASS (150 correct + 50 abstain_ok) |
| P3-L6 | seeds 1/2/3: 200/200, 0 wrong, 0 dupes | PASS x3 |
| P4 | <= 2 false refusals of 30 | 0 false refusals, 30/30 PASS |

P2 verdict changes: BUG->OK on A2 A3 A5 A6 A8 B5 C1 C2 C3 C4 C5 C7 D2 D7 E7
(H5 was already OK; it stays OK). OK->OK intermediate-reply changes only:
A1t1, H3t1 (generic clarify -> hearsay clarify), C6t1 (-> "I don't know anyone
called Zed."), C8t1 (-> "Forgotten: ..."), C8t2 ("I already have that." ->
"Saved: ..."). All other 48 cases byte-identical transcripts. P3-L2's 6th
change (new vs loop96) is RT81 `C_forget-02` ("Forget what I said about Mira's
city." -> doorway MISSING, 0 writes; listed, safe).

## What it means

The joined-up agent's English front door now tells teaching apart from
quoting, forgetting, correcting, and dating: hearsay never writes, forget
reaches the notebook's own retract path, "Actually, ..." corrects bench
shapes, year phrases don't pollute values, and bad bytes get a polite reply
instead of killing the daemon — with zero regressions.

## What it does not mean

No part was fixed in isolation (all five are seam wrappers); neural ears,
mouth53, and genuine qualifier semantics (D2/D7 drop the year phrase rather
than storing it) remain open work.

## Deviations

D1 (harness, pre-completion): P4 run 1 FAILED 20/20 teaches on a checker bug
(`new_fact_ids` key doesn't exist in the harness log; agent replies were all
correct SAVEDs). Fixed the checker to diff notebook facts, re-ran: 30/30.
D2-D5 (design, locked in PASSMARKS pre-seal): F4 drops the year phrase; bare
"online" is not a marker; the lowercase guard needs attribution vocabulary
(22 legit lowercase bench subjects); "forget Forget city" clarifies (G1).

## Questions for Ben

None.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_loop102_marks.py --mark all` (reads sealed redteam98 verdicts;
never writes outside `artifacts/fable-loop102-20260921/`). Daemon:
`uv run --offline --no-project --python 3.12 --with torch --with numpy python
-B scripts/fable_loop102_agent.py --daemon --dir DIR --config
artifacts/fable-loop102-20260921/loop102-config.json`.
