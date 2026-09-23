# Exp 102 pass marks — PATCH the 15 remaining red-team-98 bugs (sealed before the registered wave)

Loop102 = Loop96 (loop90 + GuardedEars91) + five additive fixes in
`scripts/fable_loop102_agent.py` only: F1 hearsay clarify, F2 forget via the M1
doorway, F3 correction-prefix correction, F4 trailing-year qualifier strip to
the bare value, F5 byte-safe mailbox. Every seed/case reported, never
averaged. A registered FAIL is recorded as FAIL, never re-run into a pass.
Claims never exceed evidence.

- P1: the 16 red-team-98 BUG reproducers (copies under
  `artifacts/fable-loop102-20260921/repro/`, E7 with the `(root/'inbox'/m0.txt)`
  typo fixed to `(root/'inbox'/'m0.txt')`) replayed through Loop102Daemon and
  judged against the sealed redteam98 expectations: 16/16 verdict OK, with a
  per-case before/after table (before = Loop96Daemon: H5 OK, 15 BUG).
- P2: all 64 sealed red-team-98 cases re-run through Loop102Daemon and judged
  with the unchanged `fable_redteam98_runner.judge`: 0 OK->BUG verdict changes
  vs the sealed run-2 verdicts; every changed case (verdict or reply) listed.
- P3: loop96 marks L1-L6 re-run with the loop102 agent swapped in, procedures
  and bars unchanged: L1 2/2 clarify + 0 FACT/ENTITY rows (loop90 before still
  writes); L2 74 red-team-81 cases with 0 wrong writes; L3 3/3 fix77 patterns;
  L4 RT79-18/09/53 OK with 1 site each and web-verified=0; L5-Z1 60/60 turns
  with 0 wrong writes; L5-Z2 Fable-Edit-200 200/200 in expected cell, 0 WRONG,
  0 WRITE_FAULT; L6 kill-9 + restart seeds 1/2/3 each 200/200 correct,
  0 wrong, 0 dupes.
- P4: the 30 innocent sentences sealed in
  `artifacts/fable-loop102-20260921/p4-innocent-30.json` (written before the
  agent was built) through Loop102Daemon: no teach refused, no value mangled
  vs the sealed expectation; every false refusal reported; gate: <= 2 of 30.

Deviations locked before the run: (a) F4 stores the BARE value with the year
phrase dropped, not as qualifier metadata (metadata would make the sealed
unqualified D2/D7 asks abstain); (b) bare "online" is not an F1 marker, only
"read online" (precision for people called Online); (c) the F1 lowercase
guard also requires attribution vocabulary in the subject (22 legitimate
lowercase bench subjects such as "baseball ..." exist); (d) "forget Forget
city" (sealed G1) clarifies instead of forgetting (verb/noun overlap with a
taught person called Forget); (e) E7's poison file is moved aside to done/.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_loop102_marks.py --mark all`.
Daemon: `uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_loop102_agent.py --daemon --dir DIR
--config artifacts/fable-loop102-20260921/loop102-config.json`.
