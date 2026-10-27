# Exp 139 RESULTS — value-span guard on loop129b (Muse). REGISTERED FAIL.

Target: loop139 = loop129b + ValueGuard139Mixin
(scripts/fable_fix139_valueguard.py; wrapper scripts/fable_loop139_agent.py;
config artifacts/fable-fix139-20260922/loop139-config.json). One change only:
refuse-and-clarify (exp-91 SPLIT reply) when the post-strip teach value
contains a closed-list negation/hedge word, a bare and/or outside the closed
KNOWN_AND_NAMES list, or a non-abbreviation sentence boundary.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| V1 new 56-case probe through loop139 | 0 wrong writes; >= 23/24 must-write exact | 0 wrong writes; 24/24 exact | PASS |
| V2 redteam136 re-run (145 sealed cases) | C072 C075 C082 C086 C123 C135 C136 no write; all prior-OK stay OK | 7/7 no write; 0 other verdict moves (OK 119 -> 126, WW 21 -> 14, MISSED 5 -> 5) | PASS |
| V3 marks123 suites identical + bench per-item identical | all suite verdicts identical; 600/600 per-item verdicts identical | 11 per-item correct->wrong (4 old-s2fresh + 7 new-121); bench suite PASS->FAIL; all other suites identical | FAIL |
| V4 wave < 1500 s wall-clock Mac CPU | < 1500 s | wall span exceeded (two crashed p3 attempts x 180 s + re-runs); measured runs sum 405 s | FAIL |

Suite verdicts loop139 vs loop129b: p2 FAIL=FAIL (same B7/D8, C2/C5 sets,
0 per-item moves), p3 PASS=PASS, p4 PASS=PASS, rt110 PASS=PASS (0 moves),
q1 FAIL=FAIL (F5+M5 both), bench PASS->FAIL (edit200 200/200 rows identical;
s2fresh 4 moves), rt81 FAIL=FAIL (same 61/0/13, 0 moves), sleep SKIP=SKIP,
soak PASS=PASS (2000 turns, 3 kill-9, 0 lost/wrong/doubled), q4 FAIL=FAIL
(same 7 leaks). Import-bench: edit200 150/150/0 identical incl. replies;
old-s2fresh 153 correct 4 wrong; new-121 130 correct 8 wrong (base: 136/1).

## Cause of the V3 FAIL (single cause, all 11 items)

Bench chains teach a person as citizen of "United Kingdom of Great Britain
and Ireland" (second, competing citizenship next to USA). My closed
KNOWN_AND_NAMES list (built pre-seal from *gold* answers only) holds the
"Northern Ireland" variant but not this teach-value variant, so the guard
refuses the teach and the chain answers through the USA citizenship: 10x
correct->wrong plus 1x abstain->wrong (bench121-4hop-142). Refused reply is
the existing clarify in all 11 rows. The rule as specified cannot cover real
and-names exhaustively from golds alone.

## What it means

Negations, hedges, compound values and second sentences no longer silently
enter the notebook (V1 56/56, V2 7/7, zero regressions on 119 prior-OK), but
the closed and-name allowlist is too narrow: it breaks 11/400 fresh bench
chains that route through "…Great Britain and Ireland". A follow-up rule
(e.g. allow multi-token spans, or source the list from teach values) must be
a new experiment, not an edit here.

## What it does not mean

The fix is not safe to integrate as-is (exp 138 must not stack this
version); the 11 bench wrongs are guard refusals, not model errors; nothing
here judges truth — confident single-value falsehoods still store.

## Deviations

1. scripts/fable_loop139_agent.py omitted `self.idle_seconds`, crashing
   `--daemon` subprocess suites (p3/rt110/soak); fixed with one line in my
   own new file, re-ran those suites (p3 PASS 22.5 s, rt110 PASS 72.4 s,
   soak PASS 122.4 s into marks139b after a suspected orphan overwrite of
   the first soak report; console+disk agree for marks139b).
2. First marks139 wave ran parallel to another agent's wave (contention);
   after the daemon fix all missing suites re-ran solo.
3. Pre-seal probe swaps (N04/S03/S08/W21) per PASSMARKS pre-seal evidence.

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt).
Ledger: P139.1 TRUE, P139.2 TRUE, P139.3 FALSE, P139.4 FALSE.
