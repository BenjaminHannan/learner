# 320-329 — Notebook: compact, instant, reliable at scale (nb- line)

Owner: notebook thread (cmsg_01FuvegZXjMmeUzStiEFVnEWCqGqovgrHeqzd28AgWySnb), opened 2026-09-23 19:05 UTC.
Ben (18:59 UTC): "can we compact that storage at all? I want it to be better at storing facts than a human in
reliability and scale" and "speed at which it recalls it should be instantaneous and also more accurate".

## Where we start (measured in the cloud, scratch, not registered)
- Today's notebook = one append-only JSON log (`scripts/fable_notebook_contract.py:164-183`), fsync + read-back
  on every write, sha hash chain, whole log re-read and re-verified at every start
  (`scripts/fable_fix220_restartindex.py:50-62` -> `fable_fix77_core.verify_full`), everything held in RAM.
- 20,000 facts / 2,000 people: 8.3 MB log (~375 bytes per event), 44 MB process RSS, reload 0.2 s.
  gzip -9 of the log: 1.5 MB; xz: 1.1 MB.
- Base contract `current()` scans every fact (~1 ms at 20k); the 170/142 index that 292 inherits makes asks flat
  (board: 28 ms p50 per whole ask turn at 15k facts).
- Scratch SQLite table, 1,000,000 facts / 100,000 people, integer ids, one (subject, relation) index, no raw
  sentences or hashes: 47 MB (~47 bytes per fact), lookup p50 0.004 ms / p99 0.014 ms, open ~0 s.

Ben (19:02 UTC) narrowed it: "I mean a useable notebook. If the model can't read the notebook then size doesn't
matter ... find a way to store fewer bytes per unit of information." Speed and accuracy are fine as they are.
So the MAIN target is bytes per fact in a store the model can query directly (no full load); speed, accuracy,
crash safety and tamper evidence are guard marks that must not get worse.

## What "better than a human" means here (fixed now, before any run)
- Reliability: a stored fact comes back exactly (0 wrong, 0 lost) after corrections, forgets, crashes and restarts;
  any edit to stored history is detected.
- Scale: 1,000,000 facts on a laptop with sub-second start and small memory.
- Speed: one-hop recall under 1 ms at 1,000,000 facts (storage layer only; a whole chat turn also pays the reader).
- Accuracy note: storage recall is already exact; wrong or missing answers in chat come from the reader
  (F0: 65 of 78 missed questions were never-understood teaches). This line does not claim to fix those.

## Kept, never weakened
Original sentence (raw), actor, source, provenance, rule/deps, supersedes chain, retractions, the hash chain,
append-only history (corrections add, never erase), same decisions and statuses as the contract.

## Experiments
- **nb-320 baseline (report-only):** the current store (FixedIndexedLoopNotebook, as in 292) at 20k / 100k / 1M facts
  with corrections and forgets mixed in. Bytes per fact, write rate, cold start, peak memory, 1- and 2-hop recall
  latency, recall correctness against the generator's ground truth, crash test, tamper test.
  Runner is backend-pluggable so nb-321 reuses it unchanged.
- **nb-321 compact store (one change: the storage backend).** Build task queued in parallel with nb-320 (build +
  seal + unit tests only); the registered scale comparison (nb-321-run) is queued after nb-320 is verified.
  Pass marks are fixed in the build task and copied verbatim into its sealed PASSMARKS.md.
- **nb-322 (later):** plug the verified store into 292 (the reasoner reads the in-memory indexes directly, see
  `scripts/fable_perf128_index.py:390`), with 0 reply differences on the frozen suites. Not written yet.
