# Exp 171 PASSMARKS — name-shaped values on loop138d, sealed before run

Agent: `scripts/fable_loop171_agent.py` (Loop171Ears / Loop171AgentLoop /
Loop171Daemon, build_agent171, DEFAULT_CONFIG171).
Config: `artifacts/fable-nameval171-20260922/loop171-config.json`.
Design: `design/v3/30-modes/171-name-shaped-values-muse.md` (hook points,
21 name keys each with a one-line reason, WORDS/determiner/adverb rules).
Cases: `artifacts/fable-nameval171-20260922/cases171.json` (76 cases,
110 turns: 32 clarify + 44 identical).
Word lists: `wordlist171.txt` (lowercase /usr/share/dict/words minus
`givennames171.txt`) + `givennames171.txt`; sha256 of both in
SEAL.sha256.txt. Ledger P171.1–P171.6 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Soak/rt110 flakes
under heavy load are a known mailbox race: that suite may be re-run ONCE in
the open and both reported. Heavy suites run one at a time.

## The one change (part of the seal)

NameVal171Mixin over loop138d (read-only): teach/correct on the 21 sealed
name keys (mother, father, mom, dad, mum, daddy, sister, brother, sibling,
boss, friend, spouse, wife, husband, child, son, daughter, teacher,
colleague, dog, cat) whose value's first word (lowercased) is in WORDS /
DETERMINERS / PLACE_TIME_ADVERBS writes nothing and replies with the one
sealed clarify `That sounds like a description, not a name, so I didn't
save it. What is {Name}'s {relation}'s name?` (`your …` for USER).
Everything else is the loop138d code path literally.

## Marks

- T1 (`scripts/fable_fix171_probe.py` over sealed cases171.json, fresh
  in-process loops): 76/76. 32/32 clarify (exact sealed reply, 0 writes,
  follow-up ask finds nothing: unknown-subject reply, still 0 facts);
  44/44 identical (22 real-name + 20 non-name-relation + 2 corrections:
  replies AND final triples byte-identical to loop138d on fresh loops with
  the same turns; identical cases wrote exactly the taught values).
- T2: 0 wrong writes over all 110 turns (clarify cases 0 facts; identical
  cases value-equal to taught).
- G1 (`scripts/fable_fix171_bench121.py`, reuses 138d bench driver by
  import + sealed scorer; per-item vs sealed 138b rows): exactly 4 moves,
  0 new wrong: bench121-4hop-026 + bench121-4hop-099 correct->abstain
  (spouse chain needs "Queen Sonja" / "Lady Macbeth": titles refused),
  bench132-4hop-067 correct->abstain ("Lady Macbeth"), bench132-4hop-152
  wrong->abstain (inherited 138d move). edit200 + old_s2fresh 0 moves.
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop171_agent.py
  --config artifacts/fable-nameval171-20260922/loop171-config.json --out
  artifacts/fable-nameval171-20260922/marks171 --workers 4`): per-case
  identical to the 138d frozen marks (`artifacts/fable-agent138d-20260922/
  marks138d`) EXCEPT: p4 P4-08 pass->nonpass (false_refusal: "Mira's
  mother is actually Ana." refused, "actually" is a common word; stored []
  vs ["actually Ana"]); sleep SKIP reason names the loop171 file; p3-l6
  replied_before_kill timing metadata may differ (mailbox race under load),
  verdicts identical. p2 identical (B4 fixed: Beth excluded). bench
  s2fresh-023 teach_rejects 0 (Bobby excluded). rt110/q1/q4/rt81/bench/
  sleep/soak otherwise identical modulo volatile seconds/paths. Any race
  flake re-run once in the open with both reported.
- G3 (`scripts/fable_fix171_g3.py`, reuses the 138d junk/sessions/rt143
  drivers by import with only the agent swapped; per-case vs sealed 138b
  rows AND per-case vs 138d frozen rows): 0 moves vs 138d frozen rows on
  every suite; vs 138b exactly the inherited 138d move sets, no others,
  0 new WRONG/WRONG-WRITE/junk-writes beyond 138d: redteam136 C115
  (MISSED->OK) + C124/C127/C129/C142 (OK->WRONG-WRITE, 138d M4 items);
  cases150 A03 (reply-only, OK/OK); f1 t14 (WRONG-WRITE->OK); cases139b
  C10/C21 (OK->WRONG-WRITE, 138d M4 items); redteam143 J8/K9/M3/O5/S4
  (exactly 138d's 5); sessions152 36 verdict moves + 3 new-writes
  (== 138d rows: 138d S2/S4/S5 gains + smalltalk).
- G4: every registered run < 1500 s wall-clock (< 25 min); daemon
  wrappers take idle_seconds.

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the listed sets (each itemised per-case).
- F2: any new WRONG / WRONG-WRITE / junk write vs the 138d frozen rows.
- F3: mailbox-race flakes (empty-read clarifies, lost teaches, timing
  metadata) under parallel-agent load: recorded, re-run once in the open,
  both reported.
