# Exp 171b PASSMARKS — word-names save on loop171, sealed before run

Agent: `scripts/fable_loop171b_agent.py` (Loop171bEars / Loop171bAgentLoop /
Loop171bDaemon, build_agent171b, DEFAULT_CONFIG171B), a mixin subclass of
loop171: `NameVal171BMixin` (`scripts/fable_fix171b_nameval.py`) subclasses
171's `NameVal171Mixin` and bypasses ONLY its guard (explicit super to the
exact inner-chain target the 171 guard itself delegates to), then applies
the 171b screen.
Config: `artifacts/fable-nameval171b-20260922/loop171b-config.json`.
Design: `design/v3/30-modes/171b-word-names-muse.md`.
Cases: 171's sealed `cases171.json` (76, reused read-only) + new
`cases171b.json` (46 dialogues).
Lists: 171's sealed `wordlist171.txt` + `givennames171.txt` (read-only) +
new sealed `closedlist171b.txt` (62 state/place/time words). Ledger
P171b.1–P171b.8 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Heavy suites run
one at a time.

## The one change (part of the seal)

A name-relation value (same 21 sealed name keys as 171) of ONLY 1–3
Title-case tokens (each: first letter upper, rest lower,
letters/apostrophe/hyphen only; no determiner token; no lowercase word
anywhere) counts as name-shaped and SAVES, even when its lowercase form is
a dictionary word — EXCEPT when its lowercase form is on the sealed 62-word
closed list (state/place/time words people use as descriptions), which stays
refused with 171's exact sealed clarify. Determiner-led, adverb-led, and any
value with a lowercase word stay refused exactly as in 171.

## Marks

- T1 (`scripts/fable_fix171b_probe.py` Part A over 171's sealed cases171.json,
  fresh in-process loop171b loops): 76/76, every reply/write/follow-up AND
  every stored triple byte-identical to 171's sealed `probe171.json` rows
  (171b vs fresh 138d loops also byte-identical on the 44 identical cases).
  The six 171 clarify cases whose value is Title-case-only are ALL held by
  the closed list, so nothing moves: D08 "Sick" (sick: illness state — right,
  a description), D09 "Tall" (tall: body description — right), D10 "Mean"
  (mean: temperament — right), D11 "Brown" (brown: colour description —
  right), D18 "Here" (here: place adverb — right), D19 "There" (there: place
  adverb — right). No other 171 clarify value is Title-case-only (the rest
  are lowercase-led, determiner-led, or contain a lowercase word), so no
  other case can move. Any move here is FAIL F1.
- T1b (probe Part B over sealed cases171b.json, 46 dialogues, fictional
  people only): 46/46. 16 single/double word-name saves (W01–W14: Hope,
  Grant, Rich, Ora, Faith, Iris, Pearl, Sky, Rowan, Sage, Dawn, Reed, Jade,
  Joy; W15 Hope Grace, W16 Faith Joy — each refused by 171 per its first-word
  rule, saved + answered by 171b) + 4 save-after-clarify (W17–W20: the exact
  director cases — "Zed's boss is sick." clarifies with the agent's own
  "What is Zed's boss's name?", "Zed's boss is Ora." then saves and answers;
  same for Bo/Hope, Tia/Rich, Rae/Grant) + 18 clarifies (C01–C12 lowercase
  descriptions refused as in 171, incl. "Lu's wife is a doctor."; C13–C18
  Title-case closed-list words Sick/Busy/Tired/Happy/Late/Here refused) +
  8 identical (byte-identical to 138d: real names Rita/Priya/Ana/Bea,
  non-name relations job/city, correction). Predicted vs-171 moves inside
  T1b (each 171-refused, saved + answered by 171b exactly like 138d — all
  right, all genuine names): the 20 word-name saves + I07 "Bo's dog is
  Biscuit." (biscuit is a dictionary word; Biscuit is a genuine pet name and
  138d saves it). Everything else in T1b identical to 171/138d.
- T2: 0 wrong writes over all 76 + 46 turns (clarify cases 0 facts; save /
  save-after-clarify cases store exactly the taught value; identical cases
  value-equal to taught). A description saved as a name is wrong.
- G1 (`scripts/fable_fix171b_bench121.py`, 171's driver stack by import:
  138d SPLITS/load_rows + sealed scorer, only agent/config/out swapped;
  per-item vs sealed 138b rows AND vs 171's frozen rows): vs 171 exactly
  2 moves, 0 new wrong: bench121-4hop-099 + bench132-4hop-067
  abstain→correct (their edit chains need "Lady Macbeth": 2 Title-case
  tokens, not on the closed list, so it now saves and the chains hold).
  Vs 138b exactly 2 moves, 0 new wrong: bench121-4hop-026 correct→abstain
  (inherited from 171: its chain needs "Queen Sonja of Norway", which has a
  lowercase word "of", so still refused) + bench132-4hop-152 wrong→abstain
  (inherited 138d move; "actually Ana" stays refused). edit200 +
  old_s2fresh 0 moves. Any other move or any new wrong is FAIL F1/F2.
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop171b_agent.py
  --config artifacts/fable-nameval171b-20260922/loop171b-config.json --out
  artifacts/fable-nameval171b-20260922/marks171b --workers 4`): per-case
  identical to 171's frozen marks (`marks171`) EXCEPT the sleep SKIP reason
  names `fable_loop171b_agent.py`; p2 identical; p3 verdicts identical (l5z1
  FAIL inherited; l6 only timing metadata may differ); p4 P4-08 stays
  nonpass(false_refusal, inherited: "actually Ana" is lowercase-led);
  rt110/q1/q4/rt81/bench/sleep/soak otherwise identical modulo volatile
  seconds/paths. Any other move is FAIL F1.
- G3 (`scripts/fable_fix171b_g3.py`, 171's driver stack by import with only
  the agent swapped; per-case vs 171's frozen rows AND vs sealed 138b rows):
  0 verdict moves and 0 reply diffs vs 171's frozen rows on all 6 suites;
  vs 138b exactly 171's inherited sets, 0 new WRONG / WRONG-WRITE / writes
  beyond 171 (== 138d): redteam136 C115 + C124/C127/C129/C142, cases150 A03
  (reply-only), f1 t14, cases139b C10/C21, redteam143 J8/K9/M3/O5/S4 (M3
  trips the same inherited new_wrong_vs_138b counter as 171's own driver:
  OK→WRONG-ANSWER is 138d's row), sessions152 36 verdict moves + 3 writes
  (== 171 rows == 138d rows). Any other move, any new WRONG, or any junk
  write is FAIL F1/F2.
- G4: every registered run < 1500 s wall-clock (< 25 min); daemon
  wrappers take idle_seconds.

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the listed sets (each itemised per-case).
- F2: any new WRONG / WRONG-WRITE / junk write vs the 171 frozen rows
  (== 138d rows where 171 matched 138d).
- F3: mailbox-race flakes under parallel-agent load: recorded, re-run once
  in the open, both reported.
