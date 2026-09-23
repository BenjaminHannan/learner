# 139b — Open and-name rule (Muse)

Follow-up to exp 139 (registered FAIL): the value-span guard worked, but its
closed KNOWN_AND_NAMES list was built from benchmark gold answers -- test
leakage -- and refused the real teach value "United Kingdom of Great Britain
and Ireland" (11 bench chains flipped correct -> wrong). Exp 139 stays FAIL
with one diagnosis note: closed lists sourced from golds cannot cover an
open class like names.

## The rule

On the value span AFTER the exp-129 strip, a bare "and"/"or" stores exactly
when:

(a) the "and" sits inside an "of"-phrase of a capitalised name:
    "<Capitalised words> of <Capitalised words> and <Capitalised words>"
    (exactly one "and", no "or"; name tokens start uppercase, so "Order of
    rome and paris" fails while "United Kingdom of Great Britain and
    Ireland" passes);
(b) the whole span is in OPEN_AND_NAMES: 14 UN member-state / territory
    names containing "and" (7 members: Antigua and Barbuda, Bosnia and
    Herzegovina, Saint Kitts and Nevis, Saint Vincent and the Grenadines,
    Sao Tome and Principe, Trinidad and Tobago, United Kingdom of Great
    Britain and Northern Ireland; 7 territories incl. Turks and Caicos,
    Wallis and Futuna, Saint Pierre and Miquelon), written from general
    knowledge before any run -- no bench file read to build it;
(c) everything else with a bare "and"/"or" ("Peru and Chile", "Ann and
    Bob", lower-case "peru and chile", "Tom and Ann's boss", double-and
    "Order of Rome and Paris and Oslo", "or"-in-name, bare regions like
    "North and Central America") still gets the existing clarify with no
    write -- unchanged from 139.

Negation/hedge words, sentence boundaries, the strip, and the clarify reply
are 139 verbatim (imported read-only).

## Where it sits

`ValueGuard139BMixin` (scripts/fable_fix139b_valueguard.py) replaces only
139's and/or branch; loop139b = loop129b + mixin at ears hear and loop _act
(scripts/fable_loop139b_agent.py, with `idle_seconds` from the start -- the
cause of 139's daemon crash). Subjects, relation keys, forget/ask/clarify
paths untouched; no existing file edited.

## Results (registered PASS, 4/4)

V1: 139's 56-case probe 56/56 re-run; NEW 45-case probe 45/45 (22
must-write exact: 10 invented of-names, the Ireland value, 11 UN/territory
names; 0 wrong writes). V2: redteam 136 -- 7/7 focus no-write, 0 per-case
moves (OK 126 / WW 14 / MISSED 5, same as loop139). V3: marks123 10/10 suite
verdicts identical to sealed loop129b; bench per-item 600/600 identical to
loop129b rows -- all 11 flips returned, 0 other moves. V4: 372 s < 1500 s.
See artifacts/fable-fix139b-20260922/RESULTS.md.

## What it means

Name-shaped values store exactly while packed two-fact values still refuse;
the leakage is gone (the table is principle-sourced, not gold-sourced) and
every suite, redteam, and bench row matches the base except the intended
returns.

## What it does not mean

No truth judgement -- confident false single values still store; bare
non-UN "A and B" outside an of-phrase still refuses by design, so this guard
is safe only where teaches use real names, not bare regions.
