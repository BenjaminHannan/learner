# RESULTS — Exp 212: self-router only on question-shaped turns (Muse)

## Result
PASS, 7/7 ledger predictions true. One-line change on loop138i fixes the
director-verified hijack: `My favourite colour is teal.` no longer gets
`I do not have favourites.` and `Tired is my cat's name.` no longer gets
`You never told me your name...` — both now get the base's honest decline
with nothing stored. All 49 self questions/requests answer byte-identical
to 138i, and every frozen suite, marks123 suite, bench-v3 split, and the
self-panel scorer matches the sealed 138i rows except the single predicted
row `I_edges-03`.

## Marks table (integer counts, every case reported)
| mark | bar | number | status |
|---|---|---|---|
| M1 (G, 32) | 32/32 fixed | 32 pass (138i routed D1/D2/D3/D7/D8/D10/C1/C14/C25/C27; 212 exact decline, 0 facts) | PASS |
| M2 (S, 49) | 49/49 identical | 49 pass reply+facts (23 exp99 + 8 exp100 + 8 exp105 + 4 exp187b + 6 imperative/You-are) | PASS |
| M3 rt136 (145) | 0 moves | 0 moves, 0 new wrong (OK 136 / WRONG-WRITE 6 / MISSED 3, same as sealed) | PASS |
| M3 rt143 (124) | 0 moves | 0 moves, 0 new wrong (OK 107 / MISSED 7 / WRONG-ANSWER 10) | PASS |
| M3 sessions152 | 0 moves | 0 moves, 0 new wrong/writes (OK 165 / UNHELPFUL 15) | PASS |
| M3 bench v3 (4x200) | 0 moves, 0 new wrong | 0 moves verdict+reply on all splits | PASS |
| M3 marks123 (10) | 0 moves except listed | p2/p3/p4/rt110/q1/bench/sleep/soak/q4 0 moves; rt81 1 move = predicted `I_edges-03` UNCLEAR->OK | PASS |
| M3 self105 panel | identical to sealed | scorer output identical after scrub | PASS |

The predicted `I_edges-03` move (turn `Mira`): 138i routes D4 and says
`I cannot predict.` (judge: UNCLEAR, wanted `another way`); 212 skips the
router and serves the decline, which carries the `another way` marker, so
the judge reads OK. Zero writes both sides. Reproduced in-process.

## What it means
Statements about the user or others (no `?`, first word not a
question-word/auxiliary, no you/your/yours/yourself/u/ur) never reach the
self-question router anymore; questions, imperatives like `Tell me about
yourself.`, and `You are...` turns behave exactly as before.

## What it does not mean
It does not teach the agent any new fact shapes — dropped statements now
decline honestly instead of being answered as self questions — and it does
not fix question-shaped self bugs (`Where am I from?` still misroutes).

## Deviations
One marks-bench pilot row (`bench103-s2fresh-4hop-026` wrong->abstain) did
not reproduce in 5 further runs (212 x3, 138i x2) nor in-process; recorded
as a one-off mailbox-timing flake, not a change effect. Registered run is
clean. No post-seal edits (seal 5/5 OK after all runs).

## Reproduce (Mac CPU, offline; each < 25 min, one suite at a time)
```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
U="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$U python -B scripts/fable212_marks.py --out artifacts/fable-selfgate212-20260922
$U python -B scripts/fable212_suites.py --only rt136|rt143|sessions|benchv3|marks|selfpanel --out artifacts/fable-selfgate212-20260922
shasum -a 256 -c artifacts/fable-selfgate212-20260922/SEAL.sha256.txt
```
Agent: `scripts/fable_loop212_agent.py`. Config/cases:
`artifacts/fable-selfgate212-20260922/{loop212-config,case212-g,case212-s}.json`.
Design: `design/v3/30-modes/212-selfgate-muse.md`.
