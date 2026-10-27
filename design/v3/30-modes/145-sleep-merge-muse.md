# 145 — Sleep merge: grown slots (130) + taught-beats-sleep (131), no new behaviour

Exp 130 lets sleep grow one frozen-hashed word slot past the 3 sealed slots.
Exp 131 makes an ACTIVE TAUGHT row beat an installed derivation at answer
time. Both passed. This doc merges them with zero new behaviour: the 145
agent is 130's daemon/sleeper with 131's answer rule generalised to every
word in the grown table.

## Where each piece lives (read-only parents, never edited)

- Feature A (131): `scripts/fable_sleep131_agent.py` —
  `Sleep131Reasoner(Sleep104Reasoner)`, answer override (taught-first for
  the single WORD `maternal_grandmother`, file lines 62–106);
  `Sleep131Daemon(Sleep104Daemon)` (inherits `process_file` verbatim).
- Feature B (130): `scripts/fable_sleep130_agent.py` —
  `Sleep130Reasoner(S115.Sleep115Reasoner)` (extended feed `_queue130` +
  sleep-derived relabel, lines 147–193);
  `Sleep130Sleeper(S115.Sleep115Sleeper)` (grow-one-zero-slot; free slot
  delegates to the untouched 115/wire57 `_run_exp46` path, line 538;
  else `_run_exp46_grow` with pre/post sha256 frozen hashes);
  `Sleep130Daemon(L96.Loop96Daemon)` with per-turn sleep logging.
- 115 lineage underneath: `Sleep115Reasoner.answer`
  (`scripts/fable_sleep115_agent.py`, lines 175–196) is where the
  sleep-derived relabel lives; 130 reuses that rule verbatim over
  `WORDS130`.

## The merge (one new file, `scripts/fable_sleep145_agent.py`)

- `Sleep145Reasoner(S130.Sleep130Reasoner)` overrides only `answer`. On a
  bare installed-word question (`relations == [w]`, `w` in `WORDS130`, no
  qualifiers) it resolves the entity and reads
  `notebook.current(eid, w)` filtered to `source == "taught"` — the same
  calls 131 uses. On a hit it queues the 130 episode feed exactly once
  (`_queue130`, so sleep training sees the identical feed) and returns OK
  from that row with source `taught` and the row's own fact_id trail
  (`multi` form for several rows). Every other path calls
  `super().answer` (identical queueing, derivation, sleep-derived
  relabel). This is 131's four-line routing generalised from 1 word to
  all 12 words in `WORDS130`.
- `Sleep145Sleeper(S130.Sleep130Sleeper)`: inherits the grow logic
  verbatim; only the serving filenames change (`sleep145-words.json`,
  `sleep145-SLEEPING`, entity `SLEEP145`) so 145 state never touches
  sealed 130/115 files.
- `Sleep145Daemon(S130.Sleep130Daemon)`: inherits `process_file`
  verbatim; `__init__` runs the same retrofit with the 145 reasoner.

Non-goals: no gate/recipe change, no install-blocking when a taught
word-fact exists, qualifier questions fall through to 130.

## Why it should be behaviour-preserving

G1/G3 worlds never teach a bare installed word, so the taught check never
fires there: 145 must equal 130 exactly. 116/z104 worlds only use
`maternal_grandmother` (index 0, chain mother+mother, free sealed slot),
so the 145 path is 131's rule over 130's delegation to the sealed 115
path: 145 must equal 131 exactly. T6 is the only new observable: a taught
value for a GROWN word (slot 4/5) must win at answer time.

## Verification (PASSMARKS sealed before any run)

- M1: 130's G1 (seeds 1–2) and G3 (115's L1–L3, seeds 1–3) re-run on 145
  give the same installs, probes and wrong counts as 130's wave JSONs.
- M2: 131's T1–T5 re-run on 145 pass with the same answers/sources as
  131's report, incl. E2–E4 (taught Z01/Z02/Z03 wins, source taught).
- M3 (new T6): after a GROWN slot (word 4/5) installs, teaching a value
  for that word that differs from the rule's value answers taught
  (source taught), 0 overwrites; an untaught control still derives.
- M4: full 116 red-team set through the 145 mailbox, rescored read-only
  with the corrected `.txt` lookup — no case worse than on 131.
- M5: full wave < 30 min wall clock (parallel processes, OMP=1 each).

A FAIL is recorded as FAIL with one diagnosis note; never re-run into
a pass. Every seed/case reported, never averaged.

## What it means / does not mean

Means: one sleep agent can both grow its vocabulary and respect taught
facts, with no behaviour change beyond the union. Does not mean: sleep
chooses what to learn (still a turn counter), installs are ever blocked
by taught rows (answer-time only), or growth past 12 words is tested.
