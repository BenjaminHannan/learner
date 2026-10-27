# AR1 preparation checks

The independent model worker reports 7/7 CPU software tests passed: exact model
size and initialization, label-free interface, poisoned hidden fields, request
order, native shapes, learning gradients and save/reload. The independent grader
worker reports synthetic fixtures passed all five verdicts and schema checks.
The recount worker tested synthetic raw-stream and context-agreement recounts.
None is a scientific capability result; no optimizer updates occurred.

The MPS preflight passed schedule parity, metadata/order/repetition controls and
backpropagation into context and dense blocks. A final bounded rerun records PIDs
and hashes after the pre-training bookkeeping repairs. See its JSON/log.

Panel preparation started at 2026-09-27 12:06:49 UTC, PID 54166, on Ben's Mac.
All 5,400 generated answer records passed the code checkers, including a second
load of each saved panel. A reviewer caught that cached panels initially only
checked their seed; the runner now also validates every answer, expected seeds,
kind/size counts, visible-input fingerprints and within-seed uniqueness.

**Panel overlap scope:** each seed's 600 final and 300 diagnostic requests are
mutually disjoint, as registered. Across all six seeds there are 4,478 distinct
visible inputs among 5,400 rows: grids 1,800/1,800, sums 1,800/1,800, mazes
878/1,800. Thus the preparation log's phrase “5400 unique generated rows” means
unique within each seed's pair of panels, not globally unique. Small mazes repeat
across seeds. This is reported as a limitation, not repaired by changing the
registered panel-generation rule after generation. Each separately trained model
excludes exact matches to its own final and diagnostic panels from practice;
no model weights or controller feedback pass between seeds.

AR1 software will be committed and pushed before scientific training. Research
notes may still be added during the run, but no Python sources or sealed imports
will change. Only the one local sequential MPS driver is authorized here; no
watcher, PC or unrelated process is controlled.
