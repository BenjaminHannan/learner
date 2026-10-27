# slp-364 pass marks (registered 2026-09-25, before the bench is opened or run)

Change (one): a self-check gate decides whether a night of sleep is kept (scripts/claude_slp364_gate.py).
Before the sleep it builds questions from the main notebook with plain code (taught one-hop facts, compound
words whose exact answer is computed from taught rows, and lures: broken chains and invented names), asks them
through the real reply path in a sandbox, asks them again after the sleep, and rejects the night if a taught
answer changed, a word answer names the wrong person, a lure gets a named answer, a right answer is lost, or
the sleeper says it could not run. A rejected night is undone by slp-361. Every case also has slp-360.

Twin: today's rule, the sleeper's own `accepted` flag (wire51 audit), read from the same run.
Bench: scripts/claude_slp364_bench.py, 20 faulty nights + 20 clean nights that each install something, written by
a separate agent that never saw the gate (it was told not to open it and was not told how it works). The gate
was written before the bench existed. Card test, CPU, $0. Each case: run_case -> install the gate -> one sleep.

| Mark | Bar |
|---|---|
| P364.1 faulty nights rejected | ≥ 18/20 |
| P364.2 clean nights rejected | ≤ 1/20 |
| P364.3 faults caught by the gate minus faults caught by the twin | ≥ +6 |
| P364.4 every rejected night: main notebook unchanged and nothing left unrestorable (361's report) | all |

Report only: per-category catches; the bench's own user probes after each kept night.
Proved wrong if: fewer than 14/20 faults caught, or more than 2/20 clean nights rejected.
Recorded limit, not a mark: a fact taught wrong before any question (104's case) is invisible to this gate.

## Disclosures written at seal time (before the registered run)
- The gate's code was finished after the bench agent's summary report arrived (I did not open the bench code
  before sealing). Two edits came after that report: (1) W and L count only when the reply changed during
  the night; the report said the loop has an old spouse-word quirk that names someone before any sleep, and a
  pre-existing wrong reply is not the night's fault; (2) probing sets the sleep threshold very high, because
  probes run inside the sleep and re-entered it (a hang found on my own 104 dev world). A third edit came from my
  own dev world only: replies may name people met along the chain ("I don't know G01's mother.").
- The summary told me the 8 fault category names and that 11 faults live only in memory. The gate does not
  restart the loop and has no category-specific rule.
- Sleep research round 2 asked for two fail lines: "said I don't know although the fact was present" is covered
  by T (a changed taught reply) and K (a lost right answer); "both answers of a one-fact twin pair" applies to the
  loop reasoner, not to this word-route sleeper, so it is not in 364.
- Dev check (104 world, seed 1, not in the bench): honest night kept, 0 reasons, 171 probes (T 50, W 25, L 96).
