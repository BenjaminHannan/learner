# Dry run at the reviewed commit 0d7a2e633 (2026-10-20)

**THIS IS A DRY RUN.** It uses the tiny preset, tiny visits, CPU only, and T = 120 s (procedural; BOX-SPEC "Dry-run T").
Every accuracy, ratio, step count and verdict in it is meaningless. Nothing here is a peek at the screen, and nothing
was tuned on it. It proves one thing: the box script, the runner and the readout run end to end at the reviewed commit.
Every mark of both cards is computed from the files the box writes, and the archive is packed.

```
DRYRUN=1 PIN=$(git rev-parse HEAD) OUT=.../dryrun-0d7a2e633-seal bash scripts/premonition_swarm_box.sh
# HEAD = PIN = 0d7a2e63371e54eb95d5c4dfe177c1753600c3e9, clean tree, committed manifest (47 files) OK
# exit 0 after 1,582 s; 33 steps, every rc 0
```

Host: 4-core x86_64 CPU VM, Python 3.13.16, torch 2.14.1+cpu, bash 5.2.21, no GPU. Outputs are in
`artifacts/claude-swarm-screen-20261018/dryrun-0d7a2e633-seal/` (git-ignored). Archive `swarm-screen-out.tgz` sha256
`31c092283715374ca926165ea1f5932e088957bdd44d2466674bd994f6226515` (189,800 bytes). The dry run's own checkpoints were
removed, as it is designed to do. The sha256 of `scripts/premonition_swarm_manifest.txt` is `25c117c3781f062e…`.

**What it shows:**
- **C0** ran the full protocol path: the bench via `bench()`, the time-share T, the steps-in-T ratio, and the S0
  **and** D1 eval and train-overhead probes. With the tiny override, c0.json records `registered_settings` False and
  `size` tiny, which the real box gate refuses (tested).
- **Trains:** all 9 completed, `train_seconds` 120.0-120.2 s (within ±0.2% of T).
- **Readouts:** all four computed. S0 and S1 at `--min-items 100` say INSUFFICIENT, honestly: the tiny split has
  far_deep 62, near 105 and overall 188 per file, and the new near/overall gate reports all three. At `--min-items 1`
  the full verdict paths ran (verdicts meaningless).
- **Archive:** packed by the fixed `pack`, which tars beside OUT and then moves the archive in.

## Steps (name, seconds, rc)

| step | seconds | rc |
|---|---|---|
| data | 5 | 0 |
| c0 | 167 | 0 |
| train-D1-s0 | 140 | 0 |
| train-S0-s0 | 138 | 0 |
| train-D1-s1 | 139 | 0 |
| train-S0-s1 | 139 | 0 |
| train-D1-s2 | 140 | 0 |
| train-S0-s2 | 140 | 0 |
| eval-D1-s0 | 7 | 0 |
| eval-S0-s0 | 8 | 0 |
| eval-D1-s1 | 8 | 0 |
| eval-S0-s1 | 7 | 0 |
| eval-D1-s2 | 8 | 0 |
| eval-S0-s2 | 9 | 0 |
| marks-S0 | 0 | 0 |
| marks-S0-minitems1 | 0 | 0 |
| train-S1-s0 | 140 | 0 |
| train-S1-s1 | 140 | 0 |
| train-S1-s2 | 140 | 0 |
| eval-S1-s0 | 8 | 0 |
| eval-S1-s0-board | 8 | 0 |
| eval-S1-s0-notes | 8 | 0 |
| eval-S1-s0-cards | 9 | 0 |
| eval-S1-s1 | 9 | 0 |
| eval-S1-s1-board | 9 | 0 |
| eval-S1-s1-notes | 8 | 0 |
| eval-S1-s1-cards | 8 | 0 |
| eval-S1-s2 | 8 | 0 |
| eval-S1-s2-board | 8 | 0 |
| eval-S1-s2-notes | 8 | 0 |
| eval-S1-s2-cards | 8 | 0 |
| marks-S1 | 0 | 0 |
| marks-S1-minitems1 | 0 | 0 |
