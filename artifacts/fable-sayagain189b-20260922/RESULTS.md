# Exp 189b RESULTS — widened repeat-request grammar on loop189 (Muse)

## Result: PASS

All 8 ledger predictions held. The one change (a wider repeat-request
matcher in a new subclass file) fixes the four director probes and
moves nothing else: 44/44 new-case turns, 38/38 old-case turns
byte-identical, 0 moves / 0 new wrong / 0 new writes on every frozen
suite, marks123 per-case identical apart from one predicted
timing-volatile log line.

## What changed (one change only)

`scripts/fable_loop189b_agent.py` subclasses the frozen loop189 stack.
`turn()` checks the widened matcher `is_repeat189b` FIRST, before the
unchanged loop189 path (hence before the 137d Say-pretend rule). The
closed 8-shape list becomes a small grammar, matched whole-turn and
case-insensitively: optional "could/can/would/will you" + "say/repeat"
+ optional "it / that / what you (just) said" + optional "again / one
more time / once more" + optional "please", plus bare shapes ("again?",
"what?", "huh?", "sorry, what?", "come again?", "pardon (me)?",
"what did you (just) say?", "say again"). A "Say ..." turn is a repeat
request ONLY when everything after "say" is repeat vocabulary — any
other content keeps loop189's pretend behaviour (Ben's ruling:
"Say X" = pretend). A match echoes `_prev189` (the verbatim reply of
the latest non-repeat turn; repeats never overwrite it) or the same
fixed line as loop189, "I haven't said anything yet.", and never
writes. No existing file was edited.

## Marks table (integer counts)

| Mark | Check | Result |
|---|---|---|
| W1 | sealed 44-turn session, loop189b in lockstep vs loop189 | 44/44 OK |
| W1 noprev | repeat with nothing said yet -> fixed line, 0 writes | 2/2 |
| W1 repeat | 21 new phrasings (incl. all 4 director probes) -> own previous non-repeat reply byte-identical, 0 writes | 21/21 |
| W1 traps+base | 12 traps (incl. all 7 brief-listed) + 9 teaches/asks byte-identical to loop189 (reply+triples+facts+events) | 21/21 |
| W2 | 189's sealed 38-turn cases189.json, loop189b vs loop189 | 38/38 identical |
| W3 junk | redteam136 (145) + cases150 (57) + f1 (46) + cases139b (101) vs sealed 138g rows AND 189 rows | 8 comparisons, 0 moves, 0 new WRONG/WRONG-WRITE, 0 new writes |
| W3 rt143 | 124 cases vs 138g AND 189 rows | 0 moves |
| W3 sessions152 | 180 turns vs 138g AND 189 rows | 0 moves, 0 new wrong, 0 new writes |
| W3 bench121 | 800 items / 4 splits vs 138g AND 189 rows | 8 comparisons, 0 moves, 0 new wrong |
| W3 marks123 | stock runner, per-case scrubbed-identical vs marks138g AND marks189; suite-status vectors identical (inherited p3-l5z1/p4/rt81 FAILs, overall FAIL, same as base) | 0 real diffs; 1 volatile statuses-only line (rt110 daemon log, predicted in seal); rc=1 from inherited overall FAIL |
| G4 time | longest registered run (marks123) 396.0 s wall-clock | every run < 1500 s |
| G4 seal | `shasum -a 256 -c SEAL.sha256.txt` after all runs | 5/5 OK, no post-seal edits |

Director probes now fixed: "Could you say that again?" and "What?"
echo the previous reply; "Say that one more time." echoes instead of
pretending; "Say again please." echoes instead of pretending. Traps
held: "Say hello.", "Say Kim's boss is Lee.", "Say it in French.",
"Say something nice." still pretend exactly as loop189; "Again, Kim's
boss is Lee." still teaches; "Repeat after me: Lee is kind." unchanged.

## What it means

Polite and short repeat requests ("could you...", "what?", "huh?",
"pardon me?") now repeat the last answer word-for-word without saving
anything, while every "Say X" command still pretends and never saves.

## What it does not mean

It does not rephrase, translate, or summarise — echoes are
byte-verbatim. It does not remember anything across restarts. It does
not change a single answer, score, or stored fact outside repeat
requests (proven by the 0-move frozen suites).

## Deviations

None from the sealed plan. Handoff note: a first agent sealed
PASSMARKS.md, appended ledger predictions P189b.1–8, and ran all
registered suites, then was cut off before writing RESULTS.md, the
design doc, and the outcomes line. The resuming agent verified the
seal (5/5 OK), checked every output file against the sealed
predictions, ran no new registered suites (no silent re-runs), and
wrote only the two unsealed docs plus the ledger outcomes line.

## Reproduce (Mac CPU, offline, one suite at a time, after the seal)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix189b_sayagain.py --only w1|w2|junk|rt143|sessions|bench|marks123|all
```

Outputs: `artifacts/fable-sayagain189b-20260922/` (w1-sayagain189b.json,
w2raw-sayagain189b.json, junk/redteam143/sessions/bench summaries,
marks189b/ + marks123-compare.json). Sealed inputs (never edit):
PASSMARKS.md, `scripts/fable_loop189b_agent.py`,
`scripts/fable_fix189b_sayagain.py`, cases189b.json,
loop189b-config.json.
