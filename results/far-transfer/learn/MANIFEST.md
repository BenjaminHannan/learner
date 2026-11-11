# Far transfer: checkpoints and scores pulled into the repo

Copied byte for byte from `/mnt/project-files/far-transfer/learn/` on 2026-10-16 (Whole-model roadmap thread, at Ben's request; the L12 files were first put in the shared folder by the Far transfer thread on 2026-10-16, from its own scratch space, with `L12-SHA256-2026-10-16.txt`). Every copy was re-hashed against its source; all four checkpoints open with `torch.load` (dict keys `model`, `name`, `cfg`, `chars`, `step`; the `step` field reads 24000, the parent's count, while the folder name `step_4000` is the 4,000 learning updates).

| file (under `results/far-transfer/learn/`) | bytes | sha256 | source modified |
|---|---:|---|---|
| `L12-LA64/scores.jsonl` | 5,203 | `f9fa96b358a52fd091c99c017a80cb9d2c9f22c283efa3f81811ca9c80a2d978` | 2026-10-16 02:00 UTC |
| `L12-LA64/step_4000/checkpoint.pt` | 13,286,646 | `e766966827ca6d5bea3527d3118a9e38af376862af6ed6fe61da6d9a34a20af6` | 2026-10-16 02:00 UTC |
| `L12-LB/scores.jsonl` | 5,188 | `09a648c267510c0097c285b208ab230d6b9e29ed11213a473b05fa84ef62c031` | 2026-10-16 02:00 UTC |
| `L12-LB/step_4000/checkpoint.pt` | 13,286,646 | `5468e2f7b81e6e2db13457c7793a47c88634d318497d7eb9f8c4a2290ed889cd` | 2026-10-16 02:00 UTC |
| `L12-SHA256-2026-10-16.txt` | 370 | `84acf61d2585c1f9e801f12ffbd625f9d7b9bba35502ad8d87f48db6b3d0585b` | 2026-10-16 02:00 UTC |
| `L13-LBsoft10/scores.jsonl` | 8,124 | `26c1a93348c0c0372b164f2fc8d2b21527fdb7f4cdc9000edf7bfb333fcedd69` | 2026-10-13 18:50 UTC |
| `L13-LBsoft10/step_4000/checkpoint.pt` | 13,286,646 | `b10f7917dd7494cdb328f7bf46b182e73594d6f16b59d436bd8313b8a45f7a7b` | 2026-10-13 18:50 UTC |
| `L14-LBnk30/scores.jsonl` | 8,136 | `88b964327558d690aa5c0094ed66586587af3c233f06f45e8e60f3e556af8f6a` | 2026-10-14 00:49 UTC |
| `L14-LBnk30/step_4000/checkpoint.pt` | 13,286,646 | `318ac36ce79c3cbf52ba9b5f6e8f1111cbf8aac093d7a910c3c9963b31b1f406` | 2026-10-14 00:49 UTC |

## Notes

- L12 (LA64, LB) is the join-last run: its figures stay quarantined (Ben 10-14). The files are here so the quarantined figures can be re-adjudicated or recomputed.
- The L12 checkpoints were missing from the shared folder from 2026-10-13 05:43 UTC until 2026-10-16 because they had never been copied there (they were in the Far transfer thread's scratch space), not because of a cleanup.
- glprobe/run (GW-L raw files) is not under this folder; it is in `results/game-world/glprobe-run/` (see `results/game-world/README.md`).
