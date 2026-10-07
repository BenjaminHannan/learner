# 8a growth ladder (code)

Spec: `whole-model-roadmap/8A-SPEC-2026-10-07.md` (sections 1-10, addenda A-E). Grows today's B2 (calculator inside the loop, 8 rounds) at 3M, 10M and 30M
trained parameters, depth first, on 38% own question rows + 62% FineWeb-Edu fill-in-the-blank rows, against PT (plain_tf_steps) and LLM (plain next-char LM),
plus a public model (pythia-31m) at 30M. Seeds 400-405. Everything runs on the home PC through `local_runner`; the Vast box protocol still works as a fallback.

| File | What it does |
|---|---|
| `cloze.py` | fill-in-the-blank rows from web text (chunks up to 280 letters, one 3-12 letter word blanked, deterministic) |
| `pool.py` | builds a rung's pool: nested, 38/62 by word pieces, update floor 24,000, reuse cap 4, manifest with sha256 |
| `caps.py` | caps sized from the data (addendum E): compute, apply (`train.py --caps`), report rows touched (target 0) |
| `configs.py` | rung shapes, trained-parameter counter and bands, every arm's `train.py` command (`python -m custom_io.g8a.configs` prints the table) |
| `job.py` | one rung x seed: pool, caps, arms one after another, box.json (`--local` for the PC) |
| `speed.py` | speed probe: seconds per update, peak memory, accumulation that fits 15 GB, hours and dollars per rung |
| `gh_fetch.py` | no-git fetch of code and data through the GitHub contents API (Vast fallback; needs GITHUB_TOKEN, the repo is private) |
| `get_data.py` | rebuilds the own text (xz files, hash-checked) and the web slices (FineWeb-Edu shard 0, hash-checked) on a machine without the project files |
| `../analyze_8a.py` | marks 1-5, guard, proved-wrong lines, stop rules, reported items; tested on fake numbers (`python -m custom_io.tests.test_g8a`) |
| `../models/plain_lm.py`, `plain_tf_steps_g` | the LLM arm and the depth-scalable plain arm (default shape = plain_tf_steps exactly) |

Trained sizes (default caps): 3M B2 3,302,481 (q33's) / PT and LLM 3,260,928; 10M B2 10,254,105 / 10,368,768; 30M B2 28,637,753 / 28,544,256. Sized caps change them a
little (bigger position and place tables); box.json records both.

## On the PC
Inputs (git checkouts under `WORK/8a-inputs/`): `data-pool` = branch `claude/data-pool-8b`, SPARSE (the branch is 2.2 GB; the rebuild needs only ~9 MB: `git clone --depth 1 --filter=blob:none --sparse --branch claude/data-pool-8b https://github.com/BenjaminHannan/learner data-pool` then `git -C data-pool sparse-checkout set data_pool/built data_pool/panels`, which also keeps the files directly in `data_pool/`), `own-data` = branch `claude/8a-own-data` (80 MB). `WORK/data` and `WORK/data_big` are the
skills builds `local_runner setup` already makes.

    python -m custom_io.local_runner run --work WORK --queue custom_io\queue_local\45-pc-8a-speed.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt
    python -m custom_io.local_runner run --work WORK --queue custom_io\queue_local\46-pc-8a-3m.txt   --device cuda --par 2 --busy ...   # data rebuild first, then 6 seeds
    python -m custom_io.local_runner run --work WORK --queue custom_io\queue_local\47-pc-8a-10m.txt  --device cuda --par 1 --busy ...   # only if mark 4 held
    python -m custom_io.local_runner run --work WORK --queue custom_io\queue_local\48-pc-8a-30m.txt  --device cuda --par 1 --busy ...   # only if 10M >= 3M
    python -m custom_io.analyze_8a --results WORK\results\46-pc-8a-3m WORK\results\47-pc-8a-10m WORK\results\48-pc-8a-30m --out 8a-marks.json

Queue line kinds added to `local_runner`: `g8a:` (job), `g8a-speed:` (probe), `g8a-data:` (data rebuild). Jobs wait for `WORK/data8a/READY.json`. The speed probe's
accumulation counts are read from `results/45-pc-8a-speed/8a-speed/speed.json` by every job.

Not built: an EmbeddingGemma front for the plain arms (needed only if the reader pick is EGE; the job refuses `eg_embed`).

Web slices: 3M and 10M read `slice_rung30.jsonl`, whose first documents are exactly `slice_rung10.jsonl` (byte-checked); the pool builder stops at its piece budget. The slices yield 95.5% of their token budget as cloze pieces, so a pool up to 6% short of its web budget is accepted and disclosed in its manifest (30M: web about 61% instead of 62%); more than that refuses to build.
