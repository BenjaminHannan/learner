# PASSMARKS — Exp 212: SELF-ROUTER ONLY ON QUESTION-SHAPED TURNS, on loop138i (Muse)

Agent: `scripts/fable_loop212_agent.py` (subclass; 138i and every earlier
piece read-only). Config:
`artifacts/fable-selfgate212-20260922/loop212-config.json`.
Base: loop138i (sealed rows in `artifacts/fable-agent138i-20260922/`).

THE ONE CHANGE: the self-question router call inside
`Loop138gAgentLoop.turn` (`scripts/fable_loop138g_agent.py:324`,
`intent, info = L138._route127(text)`, reached via the loop138i MRO
138i -> 138h.turn -> 138g.turn) is skipped when the turn is
statement-shaped AND contains no second-person word. Skipped = served the
base's normal decline (`S105.HONEST_DECLINE + L138.DECLINE_SUFFIX`), zero
new writes — byte-for-byte the DECLINE branch. Statement-shaped =
whitespace-normalised turn does not end with `?` and its first
`[A-Za-z]+` word (base's own `_FIRST_WORD188`) is not in `_QWORDS188` /
`_AUX188` (imported read-only from `scripts/fable_loop188_agent.py`).
Second-person (closed, whole-token): you, your, yours, yourself, u, ur.
Questions untouched (`Where am I from?` keeps its separate bug).

## M1 — G-cases (`case212-g.json`, 32 statement turns, no 2nd-person word)
Bar: 32/32 — each G-case: fresh 138i serves a NON-DECLINE self reply
(evidence of the live hijack, intents D1/D2/D3/D7/D8/D10/C1/C14/C25/C27)
and fresh 212 serves exactly the base decline with 0 stored facts.
Expected class of every G-case: `decline`, expected facts `[]`
(piloted: no G-case saves under either agent — the notebook path already
missed, so skipping the router can only decline).
Includes the two director cases: `My favourite colour is teal.` (138i D1
`I do not have favourites.`) and `Tired is my cat's name.` (138i D8).

## M2 — S-cases (`case212-s.json`, 49 self questions/requests)
Bar: 49/49 byte-identical to 138i (reply + stored facts), fresh loop per
case. Sources: 23 exp-99 canonical (C1/C2/C3/C5/C6/C8/C10/C11/C14/C15/C16/
C18/C21/C24/C26/D1/D2/D3/D5/D7/D8/D9/D10), 8 exp-100 blind
(Q01/Q05/Q11/Q15/Q29/Q41/Q51/Q60), 8 exp-105 panel
(Q001/Q009/Q015/Q021/Q029/Q031/Q035/Q039), 4 exp-187b (Q05/Q10/Q12/U01),
plus `Tell me about yourself.` / `Describe yourself.` /
`You are clever.` / `You are brave.` / `I believe you are clever.` /
`Nora baked you a pie.` (imperatives and `You are...` keep today's route
via the second-person rule; piloted identical).

## M3 — frozen suites + marks123 + bench v3 + self panel: 0 moves vs 138i
Bar per-case identical to the sealed 138i rows, 0 new WRONG / WRONG-WRITE /
junk writes, bench 0 new wrong — EXCEPT the one predicted row:
- marks-rt81 `I_edges-03` (turn `Mira`): 138i UNCLEAR (`I cannot predict.`
  via D4 + judge note `[wanted 'another way']`) -> 212 OK (the base
  decline carries the `another way` marker; facts_delta 0 both sides).
  Mechanism: bare `Mira` is statement-shaped with no second-person word,
  so the gate fires; reproduced in-process (138i D4 vs 212 DECLINE).
Predicted move list (complete): [`I_edges-03`]. Everything else 0 moves:
redteam136 (145), redteam143 (124), sessions152, marks123 suites
p2/p3/p4/rt110/q1/bench/rt81/sleep/soak/q4, bench v3 (4x200), self105
panel scorer output identical to sealed.

## Pilot notes (pre-seal, final code)
- M1 32/32, M2 49/49 (10.1 s).
- rt136/rt143/sessions/benchv3 pilots: 0 moves, 0 new wrong/writes.
- marks123 pilot: only `I_edges-03` (as predicted). One earlier pilot
  bench row (`bench103-s2fresh-4hop-026` wrong->abstain) did NOT reproduce:
  5 further bench runs (212 x3, 138i x2) plus an in-process replay all match
  the sealed rows exactly; recorded as a one-off mailbox-timing flake under
  shared-machine load, not a change effect. The registered run decides.

## Common rules
Seal: `shasum -a 256 PASSMARKS.md case212-g.json case212-s.json
scripts/fable_loop212_agent.py loop212-config.json > SEAL.sha256.txt`
BEFORE any registered run. Ledger P212.n appended before the run.
Fictional names only. Bench = base agent's drivers (v3 protocol +
marks123's own bench suite stock). Each run < 25 min Mac CPU
(OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv offline py3.12); daemon wrappers
use idle_seconds=3600. Heavy suites one at a time. Never write to the
repo-root notebook/. Post-seal code/config/case change => registered FAIL;
driver-only fix reported with diff, affected marks re-run in the open.
