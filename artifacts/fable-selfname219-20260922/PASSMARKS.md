# Exp 219 pass marks — "YOU NEVER TOLD ME" REPLIES MUST BE TRUE (sealed before the run)

One change on loop138i: every self reply that claims the user never told
or taught something is checked against the notebook before it is sent.
Agent code: scripts/fable_fix219_selfname.py + scripts/fable_loop219_agent.py
(wrapping loop138i read-only); config: loop219-config.json (this folder).
Census (scripts/fable_fix219_selfname.py census()): D8 my-name grounded HERE;
D9 age + D6 Tom already grounded by fix168 (passthrough); D5 why + C22 unsure
notebook cannot contradict (byte-identical always). Nothing here writes.

Every seed/case reported, never averaged. Fictional names only. Isolated
scratch notebook dirs (never repo-root notebook/). Mac CPU, offline,
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`.
Each run < 25 min. A registered FAIL is recorded as FAIL, never re-run into
a pass. Any change to agent code, config, or case files after the seal makes
the verdict FAIL. Base replies recorded pre-seal in base-replies.json.

- M1: 20 fresh sessions (m1-cases.json, fictional names), each teaches the
  user's name once ("My name is X.") then asks the 5 probes. PASS iff every
  reply that base 138i routes to D8 (or answers with a "never told me" claim)
  now contains the stored name, and 0 replies claim the name was never told
  while the notebook holds it.
- M2: same 5 probes with NO name taught (m2-cases.json, 5 sessions).
  PASS iff every reply byte-identical to base loop138i.
- M3: D9 age (m3-cases.json): 10 sessions with Mira's age stored (5..14) ->
  reply states the stored value; 10 sessions without -> byte-identical to base.
- M4: `python -B scripts/fable_suitediff.py --agent scripts/fable_loop219_agent.py
  --config artifacts/fable-selfname219-20260922/loop219-config.json --base 138i
  --out <dir> --only rt136,rt143,sessions152,bench` gives 0 moves
  (every moved case's detail line read, not only the summary).
- M5: `python -B scripts/fable_sleepsmoke206.py` on the new agent passes the
  same marks it passes on 138i (sleep installs, 5/5 new-people probes right,
  0 wrong, taught 50/50 dupes 0, overwrites 0, broken-chain abstains).
- M6: 0 new wrong writes anywhere (frozen suites redteam136, redteam143,
  sessions152, scripts/fable_marks123_all.py vs base; bench 0 new wrong).

Verdict PASS iff M1-M6 all pass; any miss is FAIL with one diagnosis note.
Pilots (pre-seal, same code): M1 20/20, M2 30/30 identical, M3 40/40,
suitediff rt136/rt143/sessions152/bench/marks123 all 0 moves,
sleep smoke 219 == 138i (sleeps=1 installed=1 probes=5/5 wrong=0
taught=50/50 ow=0 broken=abstain).
