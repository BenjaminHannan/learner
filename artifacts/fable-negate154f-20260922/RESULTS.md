# RESULTS — Exp 154f: plain negation removes a taught value (Muse)

## Result: PASS (N1/N2/G4). One change on loop154e: `X's R is not Y.`
retracts exactly the named taught value.

New files only (additive): `scripts/fable_loop154f_agent.py`,
`scripts/fable_fix154f_negate.py`, `scripts/fable_fix154f_buildprobe.py`,
`scripts/fable_fix154f_probe.py`, `scripts/fable_fix154f_regress.py`,
`scripts/fable_fix154f_g3.py`; artifacts
`artifacts/fable-negate154f-20260922/`; doc
`design/v3/30-modes/154f-negate-muse.md`. No other file touched, no
commits, Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`.

## Marks table (integer counts, every case reported)

| mark | bar | got |
|---|---|---|
| N1 sealed `case154f.jsonl` (90 turns, 12 segments) | 102/102 reply+writes+state checks | 102/102 PASS (1.4 s): 8 multi-valued removals (value gone, rest kept, ask lists rest), 6 single-valued removals (ask -> `I don't know …`), 8 not-a-current-value (0 events), 4 unknown names (base reply, 0 events), 19 traps identical to live loop154e |
| G1 bench 4x200 vs frozen 154e rows | 0 moves, 0 new wrong | 0 moves, 0 new wrong (800 items) |
| G2 marks123 vs `marks154e` per-case | identical except predicted volatile | verdict+reply identical all suites; suite numbers identical incl. inherited p3 l5z1/l5z2 FAILs, rt81 14 unclear; sleep SKIP filename line as predicted; 0 new WRONG/WRONG-WRITE/junk writes |
| G3 rt136 (145) + rt143 (124) + sessions152 (180 turns) | 0 moves, 0 new wrong/write | 0 moves, 0 new wrong, 0 new writes (25.6 s) |
| G4 time | each run < 1500 s | max 353.9 s (marks123); daemon idle_seconds=30.0 |
| Seal | 10/10 OK post-run, no post-seal edits | 10/10 OK (`shasum -c SEAL.sha256.txt`) |

New replies are fixed sealed sentences: hit with remainers `OK, Rana's
language is not Hindi. I still have Urdu and Bengali.`; hit with none
left `OK, Kim's boss is not Lee. I don't have another boss for Kim.`
(single-valued works: the user is the teacher); miss `I don't have
Tamil as Rana's language.` (0 events). Hit appends one notebook
RETRACT event — the same kind 154c's correct-not path uses
(`nb.retract()`). Questions, multi-hop negations, correct-not/forget
shapes, `Say`/`Pretend` prefixes and unknown names keep the loop154e
reply byte-identically.

## What it means

Saying "not" plainly now deletes exactly the fact you named, and
nothing else — on any relation you can teach.

## What it does not mean

It does not guess, infer, or touch anything you didn't name; it does
not change multi-hop, question, or correct-not handling.

## Deviations

Two ad-hoc pilot turns wrote to the untracked repo-root `notebook/`
(state_dir `.`); all drivers use isolated state dirs afterwards.
Volatile-only diffs listed in PASSMARKS.md (timestamps, random
event-ids, rt110 log-flush `statuses` race, l6 kill-timing race —
l6 spawns the loop96 daemon, not this agent).

## Reproduce (from worktree root)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154f_probe.py --cases artifacts/fable-negate154f-20260922/case154f.jsonl --out artifacts/fable-negate154f-20260922/probe154f
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154f_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154f_regress.py --bench --out artifacts/fable-negate154f-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154f_regress.py --marks p2,p3,p4,rt110,q1,bench,rt81,sleep,soak --workers 4 --out artifacts/fable-negate154f-20260922
```

## Questions for Ben

None.
