# RESULTS — Exp 154g: "No," corrections replace on multi-valued relations (Muse)

Base: loop154e (`scripts/fable_loop154e_agent.py`), subclassed read-only;
0 tracked files modified. Agent: `Loop154gAgentLoop`
(`scripts/fable_loop154g_agent.py`); helpers
`scripts/fable_fix154g_nocorrect.py`. The one change: a bare
"<No,|Actually,|Correction:> X's R is Y." (R multi-valued per
`is_multi154e`) replaces instead of adding -- 1 value: replace with
`Saved: X's R is Y. (It was Z.)`; 2+ values: 0 writes + one fixed
question `Which one should Y replace: A or B?` (next turn naming one
listed value replaces it, any other turn cancels with 0 writes and runs
normally); 0 values: plain teach. Full design:
`design/v3/30-modes/154g-nocorrect-muse.md`.

## Marks table (integer counts, every seed/case reported)

| mark | bar (sealed) | number | status | secs |
|---|---|---|---|---|
| C1 probe (91 turns, 4 segs) | 95/95 lines exact | 95/95 (91+4 resets) | PASS | 0.4 |
| quotas | 8 repl / 6 Q+A / 4 cancel / 3 noval / 12+ traps | 8 / 6 / 4 (0 writes each) / 3 / 19 traps, 19/19 reply+event identical to 154e | PASS | — |
| G1 bench 4x200 | 0 moves, 0 new wrong (predicted EMPTY) | 0 moves, 0 new wrong | PASS | 105.9 |
| G2 marks123 | per-case identical except predicted + volatile | 11/11 reports IDENTICAL; 0 diffs; bench replies all identical | PASS* | 483.3 |
| G3 rt136/rt143/sessions | 0 moves, 0 new wrong/write (predicted EMPTY) | 145/124/6 sessions: 0 moves, 0 new wrong | PASS | 30.5 |
| G4 clock | every run < 1500 s | max 483.3 | PASS | — |

*G2 suite verdicts p3 FAIL (l5z1/l5z2) and rt81 FAIL (60/0/14) are
inherited byte-identical from marks154e (pre-existing bars); 0
case-moves, so G2 PASSES its regression bar. Open pre-seal pilot had
shown 2 rt110 log-`statuses` diffs, diagnosed as a harness read race
(reply lands in done/ before the turn event is appended to
daemon.log.jsonl; the full records were verified present in the case
daemon logs) and covered by the sealed volatility rule; the registered
run needed no recourse (0 diffs).

Predictions: P154g.1 TRUE | P154g.2 TRUE | P154g.3 TRUE | P154g.4 TRUE |
P154g.5 TRUE | P154g.6 TRUE. 6/6.

## Deviations / notes

1. Case file hand-written (91 expects hand-predicted first); open pilot
   found 2 code bugs pre-seal (regex group index; Correction: turns
   need no base-triple cross-check since the 137 upgrade eats them) --
   fixed before the seal, never after (`shasum -c SEAL.sha256.txt`
   10/10 OK post-run).
2. Trap differential (open): 19/19 trap turns reply-equal to loop154e
   with structurally equal events (entity ids normalised; volatile
   event_id hex suffixes excepted).
3. Base single-valued correction style is `Saved: ...`; the sealed
   replace reply keeps it and names the old value (`(It was Z.)`). The
   contract sets `supersedes` only on functional relations, so the
   multi-valued replace is one taught FACT (correction=True, the exact
   base call) + one RETRACT -- the same two kinds correct-not writes.

## Questions for Ben

None -- probe implemented exactly (replace on "No,", ask on several).

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154g_probe.py --cases artifacts/fable-nocorrect154g-20260922/case154g.jsonl --out artifacts/fable-nocorrect154g-20260922/probe154g --state-dir <fresh-dir>
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154g_regress.py --bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154g_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154g_regress.py --marks p2,p3,p4,rt110,q1,bench,rt81,sleep,soak --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154g_regress.py --compare-marks
```

## What it means

Saying "No, Rana's language is Urdu." now fixes Rana's language to
Urdu (ask shows only Urdu) instead of collecting Hindi beside it; with
two or more languages the assistant asks which one to replace, and any
other next turn still works normally.

## What it does not mean

It does not change plain teaches (they still add), correct-not and
forget-one forms, single-valued relations, or any frozen suite
(all 0-move); it never guesses which value to replace.
