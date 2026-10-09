Consolidation-sleep confirm learners (10-09), 12 checkpoints, kept so they are not lost with the cloud container. Not for merging.

- `<parent>/fd/learner.pt`: the fresh-dream sleep (256 updates, the model's kept best checkpoint) for parents s200-s205.
- `<parent>/rp/learner.pt`: the replay-only control (256 updates, batch 512, the same skills rows).
- Every N they start from was rebuilt on the cloud CPU with `creative.fastsleep setup --T 3.0` from the B2 parents on branches
  `claude/b2-confirm-checkpoints` (s200-s205).
- Results, marks and code: branch `claude/friendly-bohr-z4dpfo`, `creative/results/fastsleep/consol/` (README.md, MARKS.md, confirm/), PR 53.
- Load with `creative.sleep.load_parent(path)`. Hashes: `SHA256SUMS` (also `confirm/LEARNERS.sha256` on the results branch).
