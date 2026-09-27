# Exp 223 PASSMARKS — capability questions pass the negation screen (sealed before any registered run)

Base: loop138i (config artifacts/fable-agent138i-20260922/loop138i-config.json).
Agent: scripts/fable_loop223_agent.py (loop138i subclass; THE ONE CHANGE: a
"?" turn the 148 screen would stop skips the screen iff the base's own
route127 intent is C24/C25 AND the turn has a second-person word
you/your/yours/yourself). No router widening, no new reply text.

Shared setup for M1/M2 (scripts/fable_loop223_probe.py): fresh loop pair
per case in isolated scratch dirs (never repo-root notebook/), same 4
fictional teaches on both (Kim's city is Oslo. / Kim's boss is Lee. /
Kim's job is baker. / Lee's city is Bergen.), then 1 case question.
Per-case router intent from the base's own call (L138._route127).
Expected capability sheets from the base's own answerer
(G168.grounded_self_answer on the BASE loop): C25 = fixed CANNOT sheet
("I cannot: feel feelings or have favourites or opinions; guess, predict
the future, or explain why things are so; believe the web on my own;
remember anything nobody taught me; know anything from outside our turns,
like yesterday; dream."), C24 = fixed CAN sheet. Stored-facts fingerprint
= semantic triples + supersede pairs (chain hashes excluded: event_id
carries a per-build random suffix).

Cases: artifacts/fable-cantdo223-20260922/questions223.jsonl (22 A + 32 B
+ 22 C = 76, written before the pilot; each run on loop138i first).
Pilot (dry, pre-seal): probe 22/22 + 54/54, 0 writes; router intents:
A09 "What don't you do?", A11 "What will you never do?", A12 "What are
things you will never do?" route DECLINE (kept, marked "not capability",
expect byte-identical; router never widened); all other 19 A-cases route
C25; all 32 B-cases route DECLINE/D7 (non-capability, stay screened).

- M1: all 22 A-cases pass: the 19 C25 cases get exactly exp_c25, the 3
  DECLINE cases byte-identical to 138i; 0 question-turn writes (either
  agent). Falsified by any wrong reply or any write.
- M2: all 54 B- and C-cases byte-identical to 138i (reply + stored-facts
  fingerprint). Falsified by any mismatch.
- M3: python -B scripts/fable_suitediff.py --agent
  scripts/fable_loop223_agent.py --config
  artifacts/fable-cantdo223-20260922/loop223-config.json --base 138i --out
  <dir> --only rt136,rt143,sessions152,bench gives 0 moves on every suite
  (every moved case's detail line read, not only the summary). Falsified
  by any move. Dry pilots pre-seal: rt136 0, rt143 0, sessions152 0,
  bench 0 (200/200 splits: 187/9/4, 195/5/0, 149/51/0, 191/9/0).
- M4: scripts/fable_sleepsmoke206.py on loop223 passes the same marks it
  passes on 138i. Dry pilots: both
  sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0 abst=0
  broken=abstain taught=50/50 ow=0. Falsified by any divergence.
- M5: 0 new wrong writes anywhere (probe write-parity + suitediff new
  WRONG/WRONG-WRITE/junk accounting incl. marks123 dry 0 moves).
  Falsified by any new WRONG, WRONG-WRITE, or junk write.

Verdict PASS iff M1-M5 all pass; any miss is FAIL with one diagnosis
note. Every seed/case reported, never averaged. Registered FAIL is
recorded as FAIL, never re-run into a pass. Claims never exceed
evidence. Env: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B ...`, one suite at a time, each run < 25 min; daemon wrappers
use idle_seconds. Never opens reading94/reading94b/naturalpanel208.

Sealed files (shasum -a 256, SEAL.sha256.txt): PASSMARKS.md,
questions223.jsonl, loop223-config.json, scripts/fable_loop223_agent.py,
scripts/fable_loop223_probe.py.
