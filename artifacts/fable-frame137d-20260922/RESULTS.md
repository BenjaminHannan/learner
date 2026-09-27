# RESULTS — Exp 137d: non-assertive framings never write (Muse, 2026-09-22)

Result first: the one-change mixin ends the WRONG-WRITE class — all 46
framed sessions reply exactly with 0 writes ("Supposedly Kim's boss is
Lee." no longer saves `[Supposedly Kim,boss,Lee]`; "Say Kim's boss is
Lee." echoes + parenthetical, never saves), and later questions answer
only from real saved facts. Zero new writes on every regression run.
Two regression marks record FAIL for one shared, diagnosed reason: 7
frozen judge checks hard-code loop137c's old "Do you know that
yourself..." hearsay reply, which Ben's mandated exact hearsay
sentence replaces (6 cases150 OK->WRONG-REPLY, 1 rt110-T6 OK->BUG; all
7 store nothing). No silent re-runs; no post-seal edits (`shasum -c`
passes).

Step 1 (asked): 137c's marker list is at
`scripts/fable_fix137c_hypo.py:48-60` (`_MARKERS`). The Supposedly junk
path: not hypothetical -> fall-through at
`scripts/fable_loop137c_agent.py:84` -> base pipeline parses
"Supposedly Kim" as a possessive subject and SAVES it (live-verified
on the base pre-seal).

## Marks (every seed/case reported; deterministic, no seeds)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (76 cases) | 76/76 OK | S-say 16/16 (say x8 + say that x8, fillers/case twins, 6 relations, exact echo+parenthetical); S-hear 24/24 (all 11 markers x2 + 2 twins, exact hearsay sentence); C 6/6 (real value answered); N 12/12 + O 18/18 identical to 137c | PASS |
| T2 wrong writes | 0 | 0 writes on all 46 framed turns | PASS |
| G1 bench (800) | 0 new wrong, moves predicted (none) | new 194/4, old 198/0, edit200 150/50/0, bench132 196/2; 0 verdict + 0 reply moves | PASS |
| G2 marks123 | per-case = marks137c except predicted (sleep reason only) | p2/p4/q1/bench/q4/soak identical; sleep SKIP reason names new file (predicted); rt81 60/0/14 + p3 l5z1 58/60 identical (inherited FAILs); p3-l6 verdicts pass (timing metadata only, known race); rt110 1 move: T6 OK->BUG (unpredicted, see diagnosis) | FAIL (diagnosis below) |
| G3 junk/sessions | 0 new WRONG/WRONG-WRITE, moves predicted | rt136 145: 0 verdict moves (C101/C102 stay OK, replies move to hearsay sentence, verdict-only compare); sessions 129 OK/2 WRONG both arms, 0 moves; rt143 106/7/11 both arms, 0 moves; f1 45/46+1 + 139b 101/101, 0 moves; cases150: 6 moves R02/R03/R04/R05/R08/A01 OK->WRONG-REPLY (reply move predicted, verdict move not) | FAIL (same diagnosis) |
| G4 time | each run < 1500 s | probe 1.1, bench 56.3, junk 8.3, sessions 11.8, rt143 22.5, marks123 311.9, rt110 open re-run 249.6 | PASS |

Diagnosis (one note for both FAILs): the 7 moves are reply-text
checks, not writes. Frozen cases150 (`reply: hearsay` needs "hear it
somewhere") and rt110-T6 (turn-1 needs "Do you know that yourself")
hard-code loop137c's old decline; the task mandates the exact new
hearsay sentence, so the checks fail while stored triples stay [].
Safety holds (0 framed writes everywhere); judge-text parity does not.
Open rt110 re-run reproduces T6 BUG identically (61/62 same, 0 harness
errors) — systematic, not the mailbox flake; soak needed no re-run
(clean 2000/0/0-0-0).

## Deviations

P137d.5 falsified on "verdict stays OK" (got 6 OK->WRONG-REPLY);
P137d.4 falsified on "no other move" (T6). All other ledger
predictions held. My pre-seal rt110 scan read top-level text keys and
missed `steps[].text` (where T6's "Apparently ..." lives) — scanning
bug, disclosed; the move is deterministic and reported, never hidden.

## What it means

Sentence-initial "Say (that) X" echoes + parenthetical and hearsay-led
turns get the exact hearsay sentence — neither ever writes, and
follow-ups answer only real saved facts; everything else is
bit-identical to loop137c.

## What it does not mean

Not a change to what counts as evidence (framed content is refused,
never modelled); 7 frozen judge reply-text checks still expect the old
wording and are recorded as FAIL rather than re-run or patched.

Seal `SEAL.sha256.txt` (9 files, verified post-run), ledger P137d.1-6
pre-run + outcomes appended post-run. Mac CPU, offline, OMP/MKL=1.
Reproduce: `… python -B scripts/fable_fix137d_probe.py`; `… python -B
scripts/fable_fix137d_bench.py`; `… python -B
scripts/fable_fix137d_junk.py`; `… python -B
scripts/fable_fix137d_sessions.py`; `… python -B
scripts/fable_fix137d_redteam143.py`; `… python -B
scripts/fable_marks123_all.py --agent scripts/fable_loop137d_agent.py
--config artifacts/fable-frame137d-20260922/loop137d-config.json --out
artifacts/fable-frame137d-20260922/marks137d --workers 4`.
Questions for Ben: should the 7 frozen judge expectations be updated
to the mandated hearsay reply (a future exp), or stay frozen as
witnesses? I default to staying frozen.
