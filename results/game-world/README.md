# Game world: GW-L raw files (`glprobe-run/`)

The Game world thread's scratch folder `glprobe/run`, copied unchanged to `/mnt/project-files/game-world/glprobe-run/` by that thread (with `glprobe-run.sha256`) and then into this repo on 2026-10-16 by the Whole-model roadmap thread, at Ben's request.

- 94 files, 166 MB, largest file 13.3 MB. All 94 re-checked here against `glprobe-run.sha256` (run `cd glprobe-run && sha256sum -c ../glprobe-run.sha256`; the paths in the list are relative to `glprobe-run/`).
- Layout: `s200/` and `s201/` (two seeds) each hold `n1000`, `n4000`, `n16000`, `n64000` (student checkpoint, `train.json`/`train.out`, `eval.json`/`eval.out`, and where present `score-sample.*` and `score-top.*`, the per-world game score files); `parents/` (the starting checkpoints, including `gwp8-s200.pt` / `gwp8-s201.pt`); `data/` and `data64k/` (the labeller's training data); `score-oracle.json` (the labeller's own per-world scores); the pipeline scripts and `progress.log`.
- `code-commit.txt` names the code commit the run used (`a3e57da490...`); that code is on the Game world branch, not in this folder.
- Not checked by me: that the scores recompute. This folder only makes the raw files available.
