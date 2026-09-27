# Exp 226 — source questions about the last reply — PASS MARKS (sealed before the registered run)

Agent: scripts/fable_loop226_agent.py (loop138i + Source226Mixin). Config: artifacts/fable-source226-20260922/loop226-config.json.
Base: loop138i (scripts/fable_loop138i_agent.py, artifacts/fable-agent138i-20260922/loop138i-config.json).
Cases: artifacts/fable-source226-20260922/cases226.json (67 sessions, 72 source turns, 133 non-source turns; fictional names; written by scripts/fable_source226_cases.py before any run of either agent).
Driver/judge: scripts/fable_source226_run.py (in-process daemon per session, isolated scratch notebook, "<RESTART>" rebuilds the daemon on the same dir).

Verdict PASS only if ALL of P1–P5 hold; any change to sealed files after the seal = FAIL.

- P1: 72/72 source turns get exactly the expected reply (types: saved city/boss/employer/language/correction, one-fact answer, 2-hop chain, 3-hop chain, worked out backwards (153 reverse), multi-valued answer, 154d yes/no, me-name saved + answer, no-fact: first turn, small talk, decline, missing fact, forget, empty reverse, capability sheet, restart; restart between answer and source question; asked twice; context moves on).
- P2: 133/133 non-source turns in the same sessions byte-identical to 138i (reply AND stored taught triples after the turn).
- P3: `python -B scripts/fable_suitediff.py --agent scripts/fable_loop226_agent.py --config artifacts/fable-source226-20260922/loop226-config.json --base 138i --out <dir> --only rt136,rt143,sessions152,bench` gives 0 moved cases (every moved-case detail line read), 0 new wrong, 0 new wrong/junk writes.
- P4: `python -B scripts/fable_sleepsmoke206.py` on loop226 passes the same marks as on 138i (artifacts/fable-sleepsmoke206-20260922/s1-138i.json): installed=True, probes 5 right / 0 wrong / 0 abstain, broken-chain probe abstains, sleep_overwrote_taught=0, taught_good=taught_total.
- P5: 72/72 source turns add 0 notebook events; 205/205 turns have stored taught triples identical to 138i (0 new wrong writes); P3 reports 0 new wrong/junk writes.

Not covered (base cannot produce them through dialogue in these sessions): web-sourced and sleep-derived facts as the answer of the last reply (the code describes their stored provenance only when the notebook holds it, else the untraced reply); the UNTRACED reply path is not sealed-tested.
