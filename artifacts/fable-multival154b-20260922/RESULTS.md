# RESULTS — Exp 154b: second values for multi-valued relations (Muse)

Base: loop138b (`scripts/fable_loop138b_agent.py`, frozen rows in
`artifacts/fable-agent138b-20260922/`). Agent: `Loop154bAgentLoop`
(`scripts/fable_loop154b_agent.py`, mixin subclass, no loop138b file
edited). Step 1 answer: YES, the contract holds two current values with
no change (`scripts/fable_notebook_contract.py:335` appends unless
`relation in self.functional`; `:413-419` multi ask; `:678-682` case c27
lifecycle proof). Full design: `design/v3/30-modes/154b-multival-muse.md`.

## The one change (sealed forms)

Non-`SINGLE_VALUED_154` relation + new different value = ADD, never a
change-prompt: `Saved: Omar's sister is Lena. (I also have Priya.)`; ask
lists oldest-first (`Omar's sister is Priya and Lena.`); 2-hop through a
2+-valued non-final hop clarifies (`…Which one do you mean?`); correct-not
and forget-one-value touch only the named value. Single-valued relations
keep loop138b's change-prompt byte-identical.

## Marks table (integer counts, every seed/case reported)

| mark | bar (sealed) | number | status | secs |
|---|---|---|---|---|
| T1 probe (81 cases) | 81/81 exact | 81/81, incl 17 add-second-value w/ list-ask, 17 single-valued identical, 8 corrections/forgets, 7 two-hop clarifies | PASS | 0.1 |
| T2 writes | 0 wrong, 0 lost | 0 wrong writes; all pinned state maps + final full_state exact | PASS | — |
| G1 bench 4x200 | moves only on multi-dup items; new wrongs only final-hop list form | 613 moves, all on multi-dup items (verified per-item; 0 on no-dup); 55 new wrong, all list-form, 0 clarify-form; correct->abstain 555, correct->wrong 55, wrong->abstain 2, wrong->wrong reply-only 1 | PASS | 35.6 |
| G2 marks123 | per-case identical to marks138b | p2 6 moves (B1,B2,B3,B5,B8,F2); p3 l5z2 flipped (mquake-twohop 100->7 correct, 47 wrong, 46 miss); rt110/rt81/q1/q4/p4/sleep/soak/bench-reversal+abstain identical | FAIL | — |
| G3 junk/redteam/sessions | 0 moves, 0 new wrong/write | rt136 145/145, rt143 124/124, sessions152 6/6 (180 turns): 0 moves, 0 new WRONG/WRONG-WRITE, 0 new writes | PASS | 6.4 |
| G4 clock | every run < 1500 s | max 257.6 (soak); probe 0.1, bench 35.6, rt110 184.1, p3 ~49, G3 6.4 | PASS | — |
| soak | 2000 turns 3 kill-9, 0 lost/wrong/doubled | turns=2000 kills=3 lost=0 wrong=0 doubled=0 (identical to 138b) | PASS | 257.6 |

Predictions: P154b.1 TRUE | P154b.2 TRUE | P154b.3 TRUE | P154b.4
FALSIFIED (G2 FAIL below) | P154b.5 TRUE | P154b.6 TRUE. 5/6.

## G2 FAIL — one diagnosis note

FAIL (recorded, not re-run). All 7 changed cases are second-teach shapes
on non-`SINGLE_VALUED_154` relations, i.e. the intended one change, not a
bug: p2 group-B/F teaches two citizenships/languages/speaks values and
expects the second to REPLACE the first (e.g. B2 Spain->Portugal expects
only `Portuguese`); 154b keeps both and lists/clarifies. Same for l5z2's
mquake-twohop edits. The sealed "0 moves" prediction rested on the
pre-seal trigger scan, whose turn parser only handles single-word
possessive subjects, so it missed p2's copula shapes (`X is a citizen of
Y`) and mquake's multi-word subjects. rt110 (62/62), rt81 (74/74), q1,
q4, p4, sleep-SKIP, soak, and bench reversal/abstain splits are per-case
identical to marks138b.

## Deviations

1. New driver `scripts/fable_fix154b_g3.py` (own prefix) written after the
seal for the registered G3 runs; G3 ran once in the open with it. Sealed
files untouched (`shasum -a 256 -c SEAL.sha256.txt` passes).
2. G2 FAIL as above; no silent re-runs. No soak/rt110 flakes observed.

## Questions for Ben

p2's group-B/F cases (and mquake edit items) treat a re-teach of
citizenship/language/etc. as a CORRECTION (replace), while 154b treats it
as a SECOND VALUE (add) — for these relations both readings are
reasonable in English. Current default: always add. If you want
"Actually, …" / explicit edits to keep replacing on multi-valued
relations too, that is a follow-up experiment, not a fix here.

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154b_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154b_regress.py --bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154b_g3.py
```

## What it means

People have several sisters, friends, children and pets; the assistant
now keeps every value taught, lists them when asked, and asks which one
you mean before reasoning through one — Priya is never silently lost.

## What it does not mean

It does not change single-valued facts (boss, mother, city still ask
before replacing), and suites that encode replace-semantics for
multi-valued relations (p2 group-B/F, mquake edits) now fail by design.
