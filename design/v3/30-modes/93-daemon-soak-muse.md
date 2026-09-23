# 93 — Daemon soak (design + registered FAIL)

Status: registered run stopped at turn 17,716 of 20,000 (K1 FAIL, ghost-tick
reply duplication after kill -9 #6). Artefacts:
`artifacts/fable-soak93-20260921/` (RESULTS.md, PASSMARKS.md, SEAL.sha256.txt,
checkpoints.csv, restarts.csv, summary.json, REPRODUCER.md). Code:
`scripts/fable_soak93_run.py` (driver), `scripts/fable_soak93_ghostdemo.py`
(deterministic mechanism demo). Nothing in exp 74 (`fable_daemon74_run.py`,
`fable_daemon74_selftest.py`) was edited — sealed sha matches exp 74.

## 1. Goal

Exp 74 proved the daemon correct at small scale (50–200 turns, fast ticks).
A soak asks the next question: 20,000 turns through a real daemon subprocess
with 5 kill -9 and 3 graceful STOP restarts at seeded-random points, checking
EVERY reply against driver ground truth and auditing the raw notebook log
after every restart. The bars (K1–K5) are in PASSMARKS.md.

## 2. Driver design

World: 2,000 one-word people (FakeEars rejects multi-word names) × 6
relations — mother/father/friend (person pointers) and city/color/food
(literals with globally unique values). Plan (seed 93, deterministic):
11,288 teaches, 2,715 `Actually, ...` corrections, 5,997 asks at 1–3 hops.
Teach-before-ask holds by construction (asks/corrections reference committed
pairs only); each pair is taught once as a plain teach (a second plain teach
would return CONFLICT by contract), later changes go through corrections,
which supersede. Reply checks: ask must contain `is <expected>.`; teach must
be `Saved: ...` or exactly `I already have that.` (DUPLICATE_OK after kill
reprocessing). Restart procedure: with the pipeline in flight, submit a
24-turn burst, sleep 0.25/0.15 s, then kill -9 or STOP; verify the chain while
stopped; reboot; await every pending reply; reconcile in order; audit
events.jsonl (one ENTITY per name; per (entity, relation) exactly as many
taught FACTs as commits, current value == ground truth). Checkpoints every
1,000 turns: RSS (`ps`), notebook bytes, wall rate, p50/p99 submit→reply
(turns straddling a restart excluded), boot and verify times. First failure
stops the run and writes REPRODUCER.md. Pipeline depth is 3 (measured drain
165 turns/s on an empty notebook vs ~70 ms sequential round trips against the
50 ms poll quantum) — small on purpose so queueing cannot inflate the K4
growth ratio.

## 3. What happened

17,716 turns in 665.5 s; restarts 1–5 clean (all audit counts 0); kill #6 at
turn 17,710 produced the first bad reply at seq 17716: `I already have that.
I already have that.` for a fact stored exactly once. Mechanism (verified in
code + deterministic demo): kill -9 between `AgentLoop.submit()`'s state save
and the end-of-step save leaves the in-flight text in `state.json`'s
loop.inbox; the rebooted daemon never drains loop.inbox itself, so the stale
text runs as a ghost tick inside the next `turn()` and its sentence joins
that turn's reply. Here ghost and real text coincided (same file
reprocessed), hence the doubling. The notebook stayed exact: post-hoc sweep
of all 17,736 logged replies shows exactly 1 bad; full audit of 10,138
taught pairs shows 0 lost, 0 duplicated, 0 wrong values. Early kills were
clean because the daemon drained the burst and was idle at kill time; the
ghost needs kill-during-turn, which only large-notebook (slow-tick) soaks
reach — exp 74's D2 could not see it. Growth is smooth (rate ~44→20/s, p50
68→145 ms, RSS 29→74 MB, boot ~0.15 s, verify ~0.06 s; pace projected ~800 s
for 20k).

## 4. Consequences and fix (for the daemon/loop owner, not this exp)

Reply stream is not exactly-once under kill-during-turn. Worse than doubling:
a resurrected turn re-executes ARBITRARY text — e.g. a stale `pick E...`
could resolve someone else's pending ambiguity, or a stale correction could
rewrite a newer value out of order. Fix at the persistence seam: on boot,
drain-or-drop loop.inbox (it is the daemon mailbox's job to hold undone
work; the loop's copy is a crash artefact), or move inbox-draining inside the
same save boundary as the tick. K1's strict reply bar did its job: without
it, this would have passed as a silent wart.

## 5. Non-goals / limits

One seed (93); template English only; StubSleeper (sleep ticks change
nothing); the K2 audit at restart 6 is out-of-sync by construction (driver
stopped before reconciling daemon-processed burst turns — the post-hoc full
sweep above replaces it as evidence, not as a mark). No re-run into a pass:
the FAIL stands; a re-soak belongs after the loop-inbox fix.
