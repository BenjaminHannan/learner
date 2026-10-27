# AR2 panel preparation

The twelve panel seeds were searched before registration; marks were pushed in `542f61b8c63e505ed02b881eb2216d57001ed1c7` before preparation or tests. `prepare_panels.py` generated and code-checked all six final/diagnostic panel files without constructing a model or updating weights. PANEL-PREPARATION.json records UTC, machine, PID, panel hashes and duplicate-rejection counts.

Each training seed has 600 final requests (200 per kind) and 300 separate diagnostic requests (100 per kind), unique and disjoint within that seed. Across the six seeds, 5,400 records represent 4,478 distinct visible inputs: 1,800 grids, 1,800 sums and 878 mazes. This follows the registered within-seed uniqueness rule. The limited maze generator repeats inputs across seeds; the new random seeds do not establish a wholly new maze universe, and pooled records must not be called independent distinct puzzles.

Grids4 is present in phase A and baseline replay, but has no scored panel here. Candidate replay uses grid5 only. Any result applies to the declared grid5 retention test; grid4 retention and general lifelong memory remain untested.
