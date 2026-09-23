# Exp 174 RESULTS — "of"-phrased chain questions (Muse)

## Result

PASS, all marks. loop174 (loop138f + one outermost ears rewrite) answers
"What is the city of Kim's boss?" as "Kim's boss's city is Oslo.", keeps
every frozen suite per-case identical to loop138f, and writes nothing new.

## What changed (one change)

`scripts/fable_fix174_chainof.py`: a question-frame rewrite, ears only.
"What/Who is the R of X's S?" -> "What/Who is X's S's R?" and "What/Who is
the R of X?" -> "What/Who is X's R?", only when R/S are in REL174 (13
surfaces read from the code: the 12 PERSON_RELATIONS of
`scripts/fable_agent_loop.py` + "city", which the base demonstrably stores
and answers) and X is a single capitalised name, questions only. The
candidate runs through the unchanged base and is used only if it parses as
an ask. Statements are never rewritten. `scripts/fable_loop174_agent.py`
stacks this mixin outermost over loop138f; nothing else changes.

## Marks table (integer counts, every case reported)

| mark | bar | got |
|---|---|---|
| T1a twin-eq (same nb) | 12/12 | 12/12 |
| T1b cross-agent twin-eq | 12/12 | 12/12 |
| T1c taught exact | 8/8 | 8/8 (incl. 2-hop n11/n17) |
| T1d untaught honest | 4/4 | 4/4 ("I don't know …", never a guess) |
| T1e traps identical | 10/10 | 10/10 |
| T1f 0 ask writes / stmt-trap no-write | 24 + 2 | 24 + 2, all delta 0 |
| T1g script identical except predicted | 12 moves | exactly n7/9/11/13/15/17/19/21/23/25/27/29 |
| T1h fire labels | 12 fire / 10 silent | 12 / 10 |
| T2 rt136 (145) | 0 moves, 0 new wrong | 0 moves, 0 new wrong (1.9 s) |
| T2 rt143 (124) | 0 moves, 0 new wrong | 0 moves, 0 new wrong (13.2 s) |
| T2 sessions (180 turns) | 0 moves/writes | 0 moves, 0 new writes (9.3 s) |
| T2 bench 800 items | 0 moves, 0 new wrong | 0 moves (194/2/4, 198/2/0, 150/50/0, 196/2/1; 59.5 s) |
| T2 marks123 (10 suites) | per-case identical | identical except 1 predicted line (sleep SKIP reason names the new agent file); p3-L5Z1 + rt81 FAIL labels inherited byte-identical (256.6 s) |
| G4 time | each run < 1500 s | max 256.6 s |

Reproduce (after seal; one suite at a time):
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_fix174_t1.py` (same for `fable_fix174_t2suites.py --only
rt136|rt143|sessions|bench`, `fable_marks123_all.py --agent
scripts/fable_loop174_agent.py --config
artifacts/fable-chainof174-20260922/loop174-config.json --out
artifacts/fable-chainof174-20260922/marks174 --workers 4`,
`fable_fix174_markscmp.py`).

## Pre-seal static evidence

`rewrite_chainof` (pure function) returns None on all 325
redteam136+redteam143+sessions152 turns, all 1005 bench questions
(edit200 + bench121-new + bench103-s2fresh), and all 168
redteam98/81/110 question literals — 0 frozen-suite firings predicted, 0
observed at runtime.

## Deviations

None. No post-seal edits (seal 8/8 clean after all runs). No re-runs: one
pilot + one registered run per suite. No commits. Fictional names only in
new teaches (traps are the brief-mandated London/Spain/France strings,
never taught). Repo-root notebook untouched (all runs in temp/artifact
dirs). Outputs ~154 MB, same scale as the base.

## Questions for Ben

None.

## What it means

"Of"-shaped chain questions now take the same answer path as the
possessive forms users already teach, with no new writes anywhere.

## What it does not mean

It does not teach "of"-statements anything new, and it does not cover
relations outside the 13-word closed list (capital, king, …) — those still
clarify exactly as before.
