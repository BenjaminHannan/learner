# Exp 170 PASSMARKS — fast asks in the stacked agent, sealed before run

Agent: `scripts/fable_loop170_agent.py` (Loop170Ears / Loop170AgentLoop /
build_agent170, DEFAULT_CONFIG170; Loop170Daemon) + THE ONE CHANGE in
`scripts/fable_fix170_compose.py` (install_index170; scans C1–C7).
Base: loop138d (`scripts/fable_loop138d_agent.py`,
`artifacts/fable-agent138d-20260922/loop138d-config.json`), read-only.
Config: `artifacts/fable-speed170-20260922/loop170-config.json`.
Design: `design/v3/30-modes/170-speed-index-muse.md`.
Drivers (all new, prefix 170): `scripts/fable_fix170_diag.py` (STEP1 profile,
unregistered), `scripts/fable_fix170_makecases.py` (sealed case generator),
`scripts/fable_fix170_replay.py` (one-arm replay), `scripts/fable_fix170_speed.py`
(S1), `scripts/fable_fix170_bench.py` (G1), `scripts/fable_fix170_soak.py` (S3).
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the case files and the code files. Ledger
P170.1–P170.10 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL with
one diagnosis note. No rule changes after the seal. Soak/rt110 flakes under
heavy load are a known mailbox race: that suite may be re-run ONCE in the
open and both reported. Heavy suites run one at a time.

## STEP1 diagnosis (unregistered, before seal)

cProfile 25 asks on the doorway-built 15k notebook with loop138d exactly as
138d M6 built it (`scripts/fable_fix170_diag.py` log:
`artifacts/fable-speed170-20260922/scratch-diag/diag.log`): 714.8 s for 25
asks; top cumulative: turn (138d:268) → agent_loop turn/step → yesno tick →
the ears mixin chain; top internal time: 3,000,450 re._compile calls
(cache misses from per-entity whole-word patterns). Per-ask full-notebook
scans: C1 notebook_triples rebuild (loop90:101); C2 whole-word mentions
re.compile per entity per composer (wordmatch149); C3 compose_n_hop triple
walks (bench92:198); C4 compose_question MQuAKE walks (bench73:246); C5
frame_consumes names build+sort (113c:112); C6 compound_subject_hit scan
(loop113:123); C7 148b screen 30k-name exemption scan (148b:141).

## The one change (part of the seal)

Same call sites, same order, same decisions; only scanning leaves read the
incremental per-(subject, relation) index (built/updated on every notebook
append): C1 cached triples list; C2 find-prefilter + cached sealed patterns
as oracle; C3/C4 walks over _sro/_srel; C5 cached names; C6 index walk +
precomputed subjects; C7 trigger pre-check (exemption scan only on hit).
Unknown shapes delegate to the saved originals. No path, screen or rewriter
skipped or reordered.

## Marks

- S1 (`scripts/fable_fix170_speed.py --cases cases-s1-asks.json --src
  <138d-work-speed2/nb138d> --outdir s1/`; each arm its own process on a
  verbatim copy of the sealed 138d M6 doorway-built 15k notebook -- reuse,
  not rebuild, is the only deviation and changes no FACT record; 25 sealed
  asks, facts[(k*37)%len] as M6): loop170 p50 < 50 ms and p99 < 200 ms,
  every reply byte-identical to loop138d's reply on the same ask.
- S2 (one-arm replay `scripts/fable_fix170_replay.py`, each arm its own
  process; 1000 sealed mixed turns on a fresh notebook
  `cases-s2-fresh.json` seed 1702, and 1000 on verbatim 15k copies
  `cases-s2-15k.json` seed 1703): every reply and every notebook state
  (canonical facts sha256 + event count) byte-identical to loop138d.
- S3 (`scripts/fable_fix170_soak.py`: 3000-turn 10-kill soak, seed 931,
  138d's driver by import): exactly-once holds (0 dup/lost/wrong) and K4
  p99 <= 300 ms.
- G1 (`scripts/fable_fix170_bench.py`, 138d bench driver shape by import):
  bench121 new + old + edit200 + bench132 per-item vs sealed 138d rows: 0
  moves; new-wrong vs loop138b: 0 beyond the one sealed 138d move
  (bench132-152 wrong->abstain, inherited).
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop170_agent.py
  --config artifacts/fable-speed170-20260922/loop170-config.json --out
  artifacts/fable-speed170-20260922/marks170 --workers 4`): every suite
  per-case verdict-identical to the 138d marks results; any race flake
  re-run once in the open with both reported.
- G3 (138d folder's drivers by import/--agent swap: redteam136, cases139b,
  redteam143, sessions152): 0 moves and 0 new WRONG / WRONG-WRITE / junk
  writes versus loop138b's frozen results
  (`artifacts/fable-agent138b-20260922/`).
- G4: every registered run < 25 min wall-clock Mac CPU; daemon wrappers
  accept idle_seconds (default 30.0).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: S1 misses only if the loaded Mac inflates per-ask past the bar while
  replies stay identical (then FAIL with the timing table, not a rescore).
- F2: any G1/G2/G3 move means an index inequivalence (diagnosis: which
  leaf), recorded per-case.
- F3: mailbox-race flakes (empty-read clarifies, lost teaches) under
  parallel-agent load: recorded, re-run once in the open, both reported.
