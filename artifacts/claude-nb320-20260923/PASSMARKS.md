# nb-320 PASSMARKS (report-only baseline of the current notebook store)

Registered 2026-09-23. This run has NO pass bars: it only reports measures.
Backend: `FixedIndexedLoopNotebook` in scripts/fable_fix220_restartindex.py
(the store model 292 uses), opened through the runner's default factory
`open_baseline(root)` -> `FixedIndexedLoopNotebook(root).nb`. No agent code
changes. Runner: scripts/claude_nb320_scale.py (takes `--factory module:attr`;
nb-321 reuses it unchanged). Workload generator:
scripts/claude_nb320_workload.py.

## Workload (deterministic, seed 3200)

- Sizes N = total operations: 20,000 / 100,000 / 1,000,000.
  Phases in order: 85% teach, 10% correction, 5% forget.
  FACT writes (assert_fact calls) = 95% of N (teach + correction).
  Relation declarations (77) and entity creations (N/10) are extra events.
- People: N/10 entities, unique fictional two-part names from invented
  syllables (e.g. "Talvo Brenash"). Never real people.
- Relations: the 77 relation names of the o0b tell/STATE rows. 30 functional
  (title occupation employer capital place_of_birth work_location school
  country city hometown home favorite_book hobby color car favorite_season
  favorite_sport instrument favorite_food favorite_color nickname
  favorite_subject allergy boss landlord coach doctor dentist vet mentor),
  the other 47 multi-valued.
- Values: 50% another entity, 50% fictional literal word. A teach never adds
  a second value to an occupied functional pair and never re-teaches an
  ever-taught value to the same pair (so every teach/correct/forget is
  expected to return SAVED; anything else is recorded as unexpected).
- Raw sentences: o0b rows (builder-outbox branch,
  artifacts/claude-own-o0b-20260923/train-00.jsonl.gz + train-01.jsonl.gz)
  with family "tell", act "STATE", count 1, one fact, mode "ASSERT",
  owner_kind "NAME" (3,754 templates). Each op reuses a template of its own
  relation with the owner span and value span spliced for subject/value.
  Corrections prefix one of 10 openers ("Actually, ", "No wait, ", ...).
  Never the "binding" family.
- Workload written once per size to /tmp/nb320/workload-<N>.jsonl, replayed
  unchanged. Probe sampling rng seed = 3200 + N (2000 one-hop, 1000 two-hop).

## Measures, per size, each step in a FRESH process (uptime logged before each)

- (a) Write: facts per second with the real fsync path, plus total wall time.
- (b) Disk: bytes of every file in the notebook dir; bytes per FACT write
      (disk / assert_fact calls) and bytes per event (disk / all events);
      gzip -9 and xz -9 sizes of events.jsonl as reference only.
- (c) Cold open: factory open of the finished dir, 3 fresh processes, median.
- (d) Peak memory of the open-and-probe process (ru_maxrss; bytes on macOS).
- (e) Recall probes scored against the generator ground truth:
      2,000 one-hop (1,200 plain taught / 400 corrected / 200 forgotten ->
      MISSING_FACT / 200 never taught -> MISSING_FACT) and 1,000 two-hop
      (first hop lands on an entity). Buckets: right / wrong value /
      missing-but-should-answer / answered-but-should-not / other status.
      Latency p50, p99, max in ms for one-hop and two-hop.
- (f) Only at 20,000: crash test (30 child processes x 3,000 facts, ack file
      fsynced per event after assert returns, SIGKILL at a random moment;
      reopen and count acknowledged-but-lost, duplicates, failed opens, torn
      tails, repairing with repair_torn_tail() where needed) and tamper test
      (20 copies of the finished log, one byte flipped at a random offset
      outside the final line, count how many opens catch it via verify_full).

## Caps and stop rules

- The 1,000,000 size stops if writing passes 90 minutes or any process
  exceeds 8 GB RSS: report DID NOT FINISH with facts written and rate so
  far, then probe what exists.
- Timings on this Mac are noisy (high load average); uptime is recorded
  before each timing step and the noise is stated, not hidden.
- Seed: 3200. GPU: no (Mac CPU only).
