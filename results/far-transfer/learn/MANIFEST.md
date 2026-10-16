# Far transfer: checkpoints and scores pulled into the repo

Copied byte for byte from `/mnt/project-files/far-transfer/learn/` on 2026-10-16 (Whole-model roadmap thread, at Ben's request). Every copy was re-hashed against its source; both checkpoints open with `torch.load` (dict keys `model`, `name`, `cfg`, `chars`, `step`; the `step` field reads 24000, the parent's count, while the folder name `step_4000` is the 4,000 learning updates).

| file (under `results/far-transfer/learn/`) | bytes | sha256 | source modified |
|---|---:|---|---|
| `L13-LBsoft10/scores.jsonl` | 8,124 | `26c1a93348c0c0372b164f2fc8d2b21527fdb7f4cdc9000edf7bfb333fcedd69` | 2026-10-13 18:50 UTC |
| `L13-LBsoft10/step_4000/checkpoint.pt` | 13,286,646 | `b10f7917dd7494cdb328f7bf46b182e73594d6f16b59d436bd8313b8a45f7a7b` | 2026-10-13 18:50 UTC |
| `L14-LBnk30/scores.jsonl` | 8,136 | `88b964327558d690aa5c0094ed66586587af3c233f06f45e8e60f3e556af8f6a` | 2026-10-14 00:49 UTC |
| `L14-LBnk30/step_4000/checkpoint.pt` | 13,286,646 | `318ac36ce79c3cbf52ba9b5f6e8f1111cbf8aac093d7a910c3c9963b31b1f406` | 2026-10-14 00:49 UTC |

## Not here

- **L12-LA64 and L12-LB final step-4000 checkpoints**: the folders `far-transfer/learn/L12-LA64/step_4000/` and `L12-LB/step_4000/` in the shared project folder are empty (both folders last changed 2026-10-13 05:43 UTC), so there is nothing to copy from here. A search of the whole shared folder and this container found no L12 `checkpoint.pt`. The Far transfer thread would have to supply them from its own scratch space, if they still exist. L12 figures are quarantined (join-last, Ben 10-14).
- **glprobe/run** (GW-L students and labeller raw per-world score files, GW-L eval files): not under this folder; it is in `results/game-world/glprobe-run/` (see `results/game-world/README.md`).
