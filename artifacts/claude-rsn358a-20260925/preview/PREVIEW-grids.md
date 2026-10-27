# Unregistered grids preview (2026-09-26 ~02:00-02:55 UTC, CPU; not a test, never the sealed files)
Small nets (plain d128 x 8 layers, loop d256 x 2 layers), 4,000 steps on 4x4/5x5 grids only, 200 fresh dev grids each.
Right of 200 (loop at the v2 stop rule; mean rounds used in brackets):
| size | plain | loop v2 stop | loop fixed 16 | loop fixed 48 |
|---|---|---|---|---|
| 5x5 (practised) | 127 | 176 (14.8) | 176 | 176 |
| 6x6 | 59 | 173 (18.2) | 173 | 174 |
| 7x7 | 24 | 131 (25.5) | 108 | 133 |
Reading: at this small scale the loop carries grids to bigger sizes far better than plain, and its stop uses more
rounds for bigger grids (at 7x7 it beats a fixed 16 rounds by 23). Suggestive only for the registered 358a run.
