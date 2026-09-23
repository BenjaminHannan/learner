# 218 — Suite-diff v2: move classes + any base (Muse)

## Problem

The shared tool `scripts/fable_suitediff.py` (exp 214) detects every
changed case but classifies weakly: a LOST CORRECT SAVE (verdict OK with
a stored fact → MISSED with nothing stored) lands in `reply-only move`,
so the summary line looks harmless to a merge reader. It also only
accepts `--base 138h|138i`, so the next base cannot be diffed.

## Design (harness only; no agent change)

New file `scripts/fable_suitediff218.py` imports `fable_suitediff`
read-only and reuses its suite runners, patching only the classifier
attribute at runtime. The 214 files are never edited. For every moved
case, classes are checked in this order: `new WRONG-WRITE`, `new
WRONG`, `new junk write` (all three exactly as 214), then `lost OK`
(base OK, new not OK), then `fixed` (base not OK, new OK), then `write
change` (stored triples or fact-write count differ), then `reply-only
move` only when verdict and stored triples are both identical and just
the reply text changed. Each per-suite summary line lists every class
count; a final `GATE: clean` line holds iff new WRONG + new WRONG-WRITE
+ new junk write + lost OK = 0 across suites run, else `GATE: NOT clean
(<counts>)`. Base lookup accepts `--base 138h|138i` or `--base-dir
<any sealed agent artifact folder>` using 214's filename search; a
suite whose rows file is absent is printed SKIPPED and recorded, never
silently passed. A `--check-table` mode scores hand-made (base, new,
expected) pairs for the classifier mark.

## Evidence

Registered: C1 12/12 pairs match; C2 director plant (`capital`→`capitol`
in input, scratch-only wrapper) yields exactly C002/C105/C118 `lost
OK`, C075/C096/C121 `reply-only move`, sessions152 clean, `GATE: NOT
clean (lost OK 3)`; C3 loop138i-vs-138i shows 0 moves on all frozen
suites both ways but 1 bench move per arm (different 4-hop items,
correct→abstain, byte-identical teaches — agent question-side
nondeterminism, see RESULTS.md diagnosis); GATE clean both ways; C4
68 s / 103 s (< 900 s). Verdict: registered FAIL on C3 by the 0-move
bar. Seal verified intact post-run. Known limitation: bench verdicts
are not OK-based, so a verdict-changing bench move with no stored
triples takes the `reply-only move` fallback label (counted, but weakly
named); a future exp could add an `answer change` class.

## Reuse

Future merges copy the one-line usage in `artifacts/
fable-suitediff218-20260922/PASSMARKS.md` and read the GATE line first:
any `lost OK` or new-wrong class blocks the merge; `fixed` / `write
change` / `reply-only move` are for the human to eyeball.
