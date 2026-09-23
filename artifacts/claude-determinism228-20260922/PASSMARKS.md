# Exp 228 PASSMARKS (sealed before registered runs)

Cause (pilot evidence): scripts/fable_fix170_compose.py `_SRC[id(list)]` outlives the list.
A recycled address makes `_src_of()` return an older notebook; the fast
`compose_n_hop` inside `fable_qrewrite132._trial_start` then fails verify, so the
rewrite never fires and the reply is a non-answer.
Fix (THE ONE CHANGE): scripts/claude_fix228_srcguard.py. `_src_of` answers only for
the live cached list object (`_TRIPLES[id(inner)][1] is triples`). Agent:
scripts/claude_loop228_agent.py (138i + guard). Config = 138i config copy.

Registered marks (all must hold for PASS):
- M1 forced flip, 138i: `claude_determinism228_forced.py` with planting. At least 30 of the
  202 target items move from correct to not-correct AND 0 items take stage
  loop138b-rewrite. Pilot: 60 flips, 0 rewrite, 60 items hit the donor.
- M2 forced flip, 228: planted verdicts are identical to 228's un-planted verdicts, item by item
  (0 moves). There are 0 donor hits and 60 rewrite-stage items. Pilot: 193/9 both ways.
- M3 loaded bench: 3 full bench runs (4 splits, 800 items) of 228 via fable_suitediff218
  `--only bench --base 138i`. Each runs with 8 extra busy processes that I start and stop
  (1-min load checked < 60 before each). Bar: 0 moves in every run and GATE clean.
- M4 frozen suites: one fable_suitediff218 run `--only rt136,rt143,sessions152 --base 138i`
  for 228. Bar: 0 moves each, GATE clean.
- M5 sleep smoke: fable_sleepsmoke206 on 228 passes as the pilot did (installed=1,
  probes 5/5, wrong=0, taught 50/50, ow=0).
- M6 hygiene: every run < 25 min; seal verifies after the runs; no post-seal edits.

Predicted moves: none, on every suite.

Informational (not marks): the pilot's 3 passive-detector runs of unchanged 138i
(scripts/claude_determinism228_detect138i.py) saw natural stale hits in runs 2 and 3.
The run-2 hit was on bench132-4hop-076, which was that run's only move.
