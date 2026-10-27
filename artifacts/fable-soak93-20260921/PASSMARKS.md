# Exp 93 PASSMARKS (sealed BEFORE the registered run, 2026-09-22)

SOAK test of the persistent daemon (exp 74, PASS). A real daemon subprocess
(scripts/fable_daemon74_run.py, unedited) is driven through its mailbox for
20,000 turns with 5 kill -9 + restart and 3 graceful STOP + restart events at
seeded-random points. Turn language is restricted to FakeEars template
sentences (teach / "Actually, ..." correct / ask 1-3 hops) over a synthetic
population of 2,000 people x 6 relations (mother/father/friend person pointers;
city/color/food literals with globally unique values). The driver keeps a
ground-truth world model and checks EVERY reply; after every restart it audits
the raw notebook log (exactly one ENTITY per name; per (entity, relation)
exactly as many taught FACT events as committed teaches, current value equal
to ground truth). Single seed 93; deterministic plan; every checkpoint reported,
never averaged.

Environment: Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_soak93_run.py --turns 20000 --seed 93
--artifact-dir artifacts/fable-soak93-20260921` (defaults: --kills 5,
--graceful 3, --budget-s 1500). Driving pipeline: up to 3 turns in flight;
reported latency is submit->reply under this sustained load; turns straddling
a restart are excluded from latency stats (they contain kill/STOP downtime).

Source sha256 (sealed; daemon files identical to exp 74's seal):
- scripts/fable_soak93_run.py 2d38a8a094f4dba0c305d70d89569a0c02ca4a6750f1535181bf32eae9a76e47
- scripts/fable_daemon74_run.py 6a206bf27b886eac3045e2c366f374fb541cafe4608309a80e94a1818c7a2380
- scripts/fable_daemon74_selftest.py ed181f17922223e0c3fe0fcf56f73ee827e86dabc984a4f262e322f1bad73140
- scripts/fable_agent_loop.py cd0b9ebab84a27bb0f11e12d930fab8fb51bd197f08ff6e1e045d480808c9ead
- scripts/fable_notebook_contract.py 7bd68fd071ef209d12683db2ac3a9b29d1d6e64990f65643436e717a7fb5ea4b
- scripts/fable_listening_m1.py e81d189e448c46d2a259762bb734ac0efa563cc0069d83f362763cdb33c78530

Marks:
- K1: 0 wrong answers and 0 wrong writes over the full 20,000 turns
  (ask reply must contain "is <expected>."; teach/correct reply must be
  "Saved: ..." or "I already have that."). Falsified by >= 1 wrong/unanswered.
- K2: no taught fact whose reply was written is lost or duplicated across the
  8 restarts (per-restart log audit: lost == 0 AND dupes == 0 AND wrongval == 0
  AND dupe_entities == 0). Falsified by any nonzero audit count.
- K3: final boot time + final chain-verification time < 10 s.
  Falsified by >= 10 s.
- K4: p99 reply latency over the last 1,000 turns < 10x p99 over the first
  1,000 turns (the growth curve is reported per-1,000-turn checkpoints).
  Falsified by ratio >= 10.
- K5: whole soak < 25 min (1500 s) wall-clock on Mac CPU, all 20,000 turns
  completed. Falsified by >= 1500 s or an incomplete run.

Falsification procedure: the first failing point stops the run; the driver
writes REPRODUCER.md (seed, turn index, text, reply, expectation) and the run
is recorded as FAIL, never re-run into a pass.

Deviations before the registered run (dev only, smoke dirs since removed):
smoke runs reused one daemon dir across invocations, which aliased stale
outbox replies and double-counted facts; the driver now starts from a fresh
daemon dir per invocation. One unexplained daemon death mid-probe (silent,
ordinary teach turn, no traceback) did not reproduce on re-run; the driver now
fails loudly with the daemon log tail if its subprocess ever dies in flight.
