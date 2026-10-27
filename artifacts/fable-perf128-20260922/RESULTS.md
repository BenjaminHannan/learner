# Exp 128 RESULTS — per-turn cost growth fix (Muse)

Diagnosis (unregistered, `diag.json`, `time.process_time()` in-process, seed-93 plan):
1k/5k/10k/15k taught facts → teach p50 4.08/13.79/24.77/38.56 ms,
correct 3.99/14.05/24.84/38.53 ms, ask 4.75/18.63/32.20/48.89 ms
(15k/1k = 9.45x/9.65x/10.3x). O(n)-per-turn scans named (file:line):
contract `current()` :246 (via `assert_fact` :331, `ask` :409); listening
`_relation()` :61; `notebook_triples()` loop90 :109 (per `hear` :133);
`_teach_action()` loop90 :160; `filtered_view77()` fix77 :157 + `known()` :244;
`_save()` agent_loop :262 (2x/turn); `process_file` set-copies loop102 :405;
`compose_question` ents+`_entity_mentions` bench73 :259/:215.

The one change (`scripts/fable_perf128_index.py`, new file only): indexed inner
notebook (incremental (subject,relation)/relation/known-relation/triples/
display/reverse/mention-bucket indexes) + index-backed ears compose, reasoner
view, teach-action, relation-declare, incremental daemon bookkeeping, and
tail-persisted state.json (full in-memory experience kept). Notebook format and
all decision logic unchanged.

## Marks (integer counts)

| mark | bar | result |
|---|---|---|
| C1 | 15k/1k CPU p50 ≤ 1.5x per kind | teach 0.762, correct 0.684, ask 0.672 (25 samples/kind) PASS |
| C2 | 5000/5000 replies identical | 5000/5000 PASS |
| C3 | P2/P3/P4 unchanged | P2 16 BUG→OK, 0 still-bug, 0 OK→BUG, 0 reply-changed; P4 30/30; P3 7/7 PASS |
| C4 | seed-93 20k soak 0 wrong/lost/dup | 0/0/0; K1–K5 all PASS; receipts 20000/20000 exactly-once PASS |
| C5 | total < 1800 s | ~1600 s PASS |

C4 wall curve (informational, contention noted), per-1000-turn p50/p99 ms —
ours: 64/89 → 96/285; exp-108 loop102: 65/75 → 228/1096. CPU flat (C1); leftover
wall growth is mailbox queueing + fsync on the bigger log, not compute.

## Deviations
- DEV-1: C1 ran 3x (run-1 FAIL 6.7x: bench73 non-template fallback still built
  full triples; run-2 FAIL ~2–3x: mentions sort still linear; run-3 PASS after
  completing the same one-change index coverage). Same theme, no bar changed.
- DEV-2: seed-93 plan holds max ~14,003 taught FACTs; the 15k point adds
  synthesized corrections on known literal pairs (diag + C1).
- DEV-3: C3 harness path bug (file vs dir), re-ran clean, PASS.
- DEV-4: C4 first launch failed (daemon CLI flag mismatch, 0 turns), fixed
  harness, re-ran clean PASS. C3 re-ran after the fix (real subprocess bursts).

## Reproduce (Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`)
- `scripts/fable_perf128_diag.py --out artifacts/fable-perf128-20260922/diag.json`
- `scripts/fable_perf128_c1.py`, `fable_perf128_c2.py`, `fable_perf128_c3.py`
- `scripts/fable_perf128_soak.py --turns 20000 --seed 93 --artifact-dir artifacts/fable-perf128-20260922/soak93`

## What it means
Per-turn CPU no longer grows with notebook size: the joined-up agent answers
in ~1–3 ms at 15k facts, and the 20k soak finishes in 587 s with zero errors.

## What it does not mean
Wall-clock under load still rises with log size (I/O + queueing, not CPU), and
nothing here changes answers, storage format, or sleep/thinking behavior.
