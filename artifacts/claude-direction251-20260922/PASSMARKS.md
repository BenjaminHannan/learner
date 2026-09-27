# Exp 251 PASSMARKS — verb direction (sealed before any registered run)

Agent: scripts/claude_loop251_agent.py (base228 + scripts/claude_fix251_direction.py)
Config: artifacts/claude-direction251-20260922/loop251-config.json (byte copy of loop228-config.json)
Base arm: scripts/claude_loop228_agent.py with the same config.
Runner: scripts/claude_direction251_run.py. Scorer: scripts/claude_direction251_score.py.
Dev cases: artifacts/claude-direction251-20260922/dev251.jsonl (52 items: 28 direction,
6 inverse, 10 must-not-change, 8 traps; fictional names; never taken from any panel).

## Registered marks (each run once)
- M1a: panel family `direction`: 10/10 right (no stated value in the reply, no question write).
- M1b: wrong values on all 124 panel items: 0.
- M1c: question writes on all 124 panel items: 0.
- M1d: control items 12/12 byte-identical to base228.jsonl base_reply.
- M1e: no item in compose / no_apos / whats / first_person / verb_subject / my_relation
  goes from base_right true to not right; untaught 10/10 give no stored value.
- M1f: combo items reported per item, no bar (a wrong value there counts in M1b).
- M2: dev: direction 28/28, inverse 6/6, must-not-change 10/10 (byte-identical to the
  same-session base arm and gold present), traps 8/8 no value, 0 question writes.
- M3: scripts/fable_suitediff218.py --base 138i --only rt136,rt143,sessions152,bench:
  0 new WRONG / WRONG-WRITE / junk write / lost OK; moves equal the predicted list.
  Predicted list: NO moves (rt136 0, rt143 0, sessions152 0, bench 0), GATE clean.
- M4: scripts/fable_sleepsmoke206.py: sleeps 1, installed 1, probes 5/5, wrong 0,
  taught 50/50, overwrote 0, under 300 s.
- M5: median over the 124 panel items of (251 question ms - base228 question ms, same
  session) <= +5 ms.
Panel: scored only after this seal, after re-checking the panel seal and running the
scorer's schema check (SCHEMA-MISMATCH -> exit 3 -> VOID, no verdict).
Verdict: PASS only if M1a-e, M2, M3, M4, M5 all pass.

## Predicted moves
- Panel direction: base228 leaks on some items (ledger P250 notes 6 base leaks,
  q243-085..090); 251 predicted 10/10 no leak.
- Panel other families: replies identical to base228 except where the question is a
  direction wording (none expected outside `direction`); 0 new wrong values.
- Dev (pilot): 14/28 direction items leak on base (employer only); 251 fixes all 14.
- Suites: no moves.

## Pilot results (before seal; not registered)
Dev 52/52 right, 0 writes. Suites 0 moves, GATE clean (41 s). Sleep smoke sleeps 1,
installed 1, 5/5, wrong 0, 50/50, ow 0, 85.8 s.

## Known risks
- The panel's direction items may use wordings outside the ten verbs and the extra list.
- The scorer counts any stated value in an ABSTAIN reply as wrong; the fix therefore
  never echoes a name that is itself a stored value in a decline.
