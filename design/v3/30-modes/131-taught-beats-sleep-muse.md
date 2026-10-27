# 131 — Taught beats sleep (answer-time fix for the exp-116 E finding)

## Problem

Exp 116 proved a critical override: `T01's maternal_grandmother is Z01`
is taught and stored active, sleep installs the mother+mother word from
clean episodes, and the daemon then answers H01 labelled sleep-derived.
The notebook is intact (0 overwrites) but the answer contradicts what
was taught. Cause: `Sleep104Reasoner.answer` delegates every bare-word
question to the inner reasoner's installed-word path. Once installed,
the word's logit stages route mother+mother and the derivation shadows
any directly taught row for the word itself. (Pre-install the same
question answers taught: the uninstalled word falls back to a plain
relation lookup. The bug is install-shadows-taught, not missing data.)

## Rule

A taught fact always beats an inference. Taught rows are ground truth
at answer time; installed skills are routing. When both exist for the
exact asked (entity, relation), the taught row answers and the record
says `taught` with that row's trail — never the derivation's.

## Change (one, additive)

`scripts/fable_sleep131_agent.py` (new; sealed 104 files untouched):

- `Sleep131Reasoner(Sleep104Reasoner)` overrides only `answer`. On a
  bare word question with the word installed and no qualifiers, it
  resolves the entity and reads `notebook.current(entity, word)`
  filtered to `source == "taught"` — the same calls existing code uses.
  On a hit it returns OK from that row (entity name or literal, trail
  `[fact_id]`, `multi` form for several rows) with source `taught`. The
  104 episode-queue call runs once first, so sleep training sees the
  identical feed. Every other path calls `super().answer` (identical
  queueing, derivation, and sleep-derived relabel).
- `Sleep131Daemon(Sleep104Daemon)` inherits `process_file` verbatim;
  `__init__` runs the same retrofit with the 131 reasoner. Sleeper,
  gate, bridge, report row, atomic word file, marker: byte-identical.

Non-goals (deliberately out): blocking or qualifying an install when a
taught word-fact exists (116's open question); any gate/recipe change;
qualifier interplay (falls through to 104).

## Why answer-time, not install-time

Three reasons. (1) Locality: the conflict is visible exactly where it
hurts — one question, one entity, one taught row — so the fix is four
lines of routing with no training or gate side effects. (2) Evidence:
the install itself is innocent (clean episodes, OOF 1.0); punishing it
would refuse good skills. (3) Generality: teach-after-sleep (exp 131
T4) cannot be fixed at install time at all — the teach arrives later —
while answer-time taught-wins covers both orders uniformly.

## Verification

Registered wave (PASSMARKS sealed abe0db57…, predictions P131.1–P131.5):

- T1: E2/E3/E4 answer Z01/Z02/Z03, source `taught`; E1 unchanged.
- T2: all 33 other 116 verdicts identical (B/D/F still sleep-derived).
- T3: all Z1–Z5 fields identical to the sealed 104 report.
- T4: post-install teach wins (Z01, `taught`, 0 overwrites) while the
  untaught control still derives (H02, sleep-derived).
- T5: 815 s wall, Mac CPU, OMP=1/MKL=1.

Deviation D1 (checker-only): the reused 116 driver reads records by
bare probe name, missing the `.txt` suffix — same bug as 116 D3.
Rescored read-only from frozen logs (`fable_sleep131_rescore.py`); raw
files kept. No daemon behaviour is in doubt: the frozen records show
`taught`/`sleep-derived` exactly as marked.

## Limits

One word slot, small families, mailbox English only. Multi-row taught
answers and qualified word questions take the conservative paths
(multi-record / 104-fallthrough) by construction but were not attacked.
A malicious or mistaken taught row now overrides a good derivation by
design — that is the rule working, and corrections (supersession) still
apply normally.
