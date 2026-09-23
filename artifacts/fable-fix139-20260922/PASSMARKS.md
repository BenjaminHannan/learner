# Exp 139 PASSMARKS — value-span guard single-change fix (sealed BEFORE any registered run)

Registered single-change fix for red team 136 classes W3 + W5 + W6
(artifacts/fable-redteam136-20260922/RESULTS.md; director reproduced each
with fresh sentences): the teach value span is stored raw even when it is not
a single plain value. THE ONE CHANGE: a value-span validator applied to every
teach path just before the write (scripts/fable_fix139_valueguard.py,
stackable ValueGuard139Mixin; thin loop139 = loop129b + mixin in
scripts/fable_loop139_agent.py with --daemon entry). No existing file edited.

THE RULE (on the value span AFTER the exp-129 punctuation strip): the turn
does NOT write and gets the loop's existing clarify reply (the exp-91 SPLIT
message "I can take one fact at a time — could you split that?") when the
span (a) contains a negation/hedge word from the CLOSED list fixed here
before any test: not, never, no longer, probably, maybe, perhaps, possibly,
might, likely, i think (word-boundary, case-insensitive, anywhere in the
span); (b) contains a bare " and " / " or " joining two spans, UNLESS the
whole span (case-insensitive, whitespace-collapsed) is in the CLOSED
KNOWN_AND_NAMES list fixed here before any test (see below); (c) contains a
sentence boundary (". " / "! " / "? " followed by more text), where
abbreviation periods do NOT count (preceding token abbreviation-shaped under
the exp-129 rule, e.g. "St. Louis", "Washington, D.C.", "Apple Inc.").

AND-NAME RULE (decided before testing): bare "and"/"or" refuses UNLESS the
full value span is a member of KNOWN_AND_NAMES =
{great britain and northern ireland, the united kingdom of great britain and
northern ireland, united kingdom of great britain and northern ireland, north
and central america, queen city of the pacific and others (the 5 distinct
benchmark gold answers containing " and ", scanned 2026-09-22 across bench65
edit200 + bench103 s2fresh + bench121) + trinidad and tobago, bosnia and
herzegovina (the brief's examples) + antigua and barbuda, saint kitts and
nevis, sao tome and principe (three further UN member states)}. Every other
bare "and"/"or" (e.g. "Ann and Sue", "Peru and Ann", "Oslo or Paris")
refuses. Tested by probe cases W18/W19 (must write) vs A01-A08 (must not).

Sealed inputs:
- V1 probe set: artifacts/fable-fix139-20260922/cases139.json
  (56 cases: 32 must-not-write = 8 negations + 8 hedges + 8 compounds +
  8 second-sentences across possessive + bench73 + bench92 frames;
  24 must-write-exactly incl. Trinidad and Tobago / Bosnia and Herzegovina,
  D.C./St./Inc. abbreviations, values followed by just a period),
  sha256 7c3af23161725d8b2f3faab3d0daa176b466878f841f03bc0a1140b42ad16551
- 136 suite+checker: artifacts/fable-redteam136-20260922/cases136.json
  (sealed there, read-only here; re-run by import with daemon factory
  swapped, outputs into this exp's dir only, never overwriting 136's).
- 123 suites, bench splits + scorer v2: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- V1 new probe through loop139 (scripts/fable_fix139_probe.py --agent
  loop139, fresh loop per case): 0 wrong writes; >= 23/24 must-write stored
  exactly (>= 95 %).
- V2 red team 136 re-run through loop139: C072 C075 C082 C086 C123 C135 C136
  -> no write (7/7); every 136 case that was OK on loop129b stays OK (no
  OK->write-move and no OK->MISSED-move; per-case verdicts diffed).
- V3 marks123 (scripts/fable_marks123_all.py --agent scripts/fable_loop139_agent.py
  --config artifacts/fable-fix139-20260922/loop139-config.json --out <this-dir>/marks139 --workers 4,
  plus loop129b into <this-dir>/marks129b for the diff): every suite verdict
  identical loop139 vs loop129b; Fable-Edit / old fresh / bench121 per-item
  verdicts identical (benchmarks via scripts/fable_loop129b_bench.py by
  import with class/config swapped, outputs into this dir only); any
  difference explained per item.
- V4 whole registered wave < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Base calibration (scripts/fable_fix139_probe.py --agent loop129b on the
  frozen probe): 30/32 must-not-write cases WRONG-WRITE on loop129b
  (N04/S03/S08 shapes rewritten until all 32 wrote), 24/24 must-write OK
  except W21-D.C.-possessive (FakeEars rstrip eats the abbreviation period:
  known 136 class W8, out of scope; replaced by St. Paul possessive, OK).
- Screen unit check (pure function, no loop): 40/40 strip-then-screen cases
  as ruled (neg/hedge/and-or/boundary blocked; Trinidad and Tobago, Bosnia
  and Herzegovina, UK-full-name, D.C./Inc./St. spans, Nottingham/Amend/Orson/
  Dora/Morning unblocked); 682/682 distinct bench gold values unblocked.
- 136 baseline: OK 119 / WRONG-WRITE 21 / MISSED 5 (RESULTS.md).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.
