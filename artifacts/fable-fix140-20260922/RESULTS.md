# Exp 140 RESULTS — one value-tail cleaner for red team 136 W4 + W7 + W8

Target: loop129b + one new mixin (`scripts/fable_fix140_tail.py`,
`scripts/fable_loop140_agent.py`; no existing file edited or read-for-write).
The exp-129 sanitizer is extended (subclass/wrap) to also drop trailing
symbol/emoji runs (So/Sk/Sm/Sc/Cf + variation selectors + ZWJ) and unmatched
trailing quotes, and the FakeEars possessive path uses this cleaner instead
of `rstrip(".")`. Subject spans get the same cleaner.

## Marks table (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 NEW 44-probe, values exact, 0 wrong writes | 44/44 + 5/5 subject | 43/44 + 5/5 | FAIL |
| T2 redteam136 focus C117 C118 C119 C126 C140 exact | 5/5 | 5/5 | PASS |
| T2 every prior-OK stays OK | 119/119 | 119/119 | PASS |
| T3 marks123 suites identical verdicts loop140 vs loop129b | all | all (0 diffs) | PASS |
| T3 bench per-item identical (600 rows, verdict + reply) | 600/600 | 600/600 | PASS |
| T4 wave < 1500 s Mac CPU | < 1500 s | 425 s | PASS |

T2 re-run: 124 OK (119 kept + 5 fixed), 16 WRONG-WRITE + 5 MISSED remain —
exactly the sealed 21 + 5 minus the 5 fixed, all out-of-scope classes
(W1/W2/W3/W5/W6 + knowns). Bench loop140: edit200 150/50/0, old_s2fresh
157/43/0, new_121 136/63/1 — the loop129b calibration numbers, 0 moves.

## Why T1 is FAIL (my probe bug, not the fix)

T030 teaches `Tom works in the field of Medicine 😀?` — it ends in `?`, so
the sealed loop121 rule routes it to the question path (clarify, no write)
on EVERY loop. Loop129b also stores nothing there (checked). A teach ending
in `?` can never be a teach; the expectation was wrong when I wrote it.
43/44 store exactly; the 7 symbol-in-name values
(Either/Or, Frost/Nixon, Frankfurt/Main, A/UX, FutureSex/LoveSounds,
Speakerboxxx/The Love Below) all survive byte-identical.

## Deviation D1 (own code, reported, re-run)

T2 run-1 passed focus 5/5 but regressed 2 prior-OKs: C077 (`boss is Bob?`)
and C138 (`mood is ...`). Cause: TailFakeEars cleaned BEFORE the exp-91
guards, erasing the `?`/empty signals they decide on. Fix (my file only):
keep the old rstrip span when it is empty or carries `?`, `;`, or >6 words,
so guard paths are base-identical; clean only spans guards would pass.
T2 run-2: 5/5 focus, 119/119 kept. T1 run-2 confirms 43/44 (T030 only).

## What it means

Emoji tails, stray closing quotes, and eaten abbreviation dots are fixed at
the source on every teach path, with zero measured behaviour change
anywhere else (0/145 redteam moves outside the 5 fixes; 0/600 bench moves;
0 marks123 verdict moves).

## What it does not mean

The other 136 junk classes (negations, officeholder chatter, second-sentence
tails, compound values, shadowed frames) are untouched and still store junk;
frequencies are per-probe, not per-user-traffic.

Questions for Ben: none.

Reproduce: PASSMARKS.md command block (sealed `SEAL.sha256.txt`).
Ledger: P140.2 TRUE | 0.0225, P140.3 TRUE | 0.04, P140.4 TRUE | 0.01,
P140.1 FALSE | 0.64 (probe-design miss, identical on base).
