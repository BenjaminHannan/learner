# Incident 1 — rented box too slow; remote wave aborted before any scoring (2026-09-20)

* Box: vast.ai instance 51770722, whole AMD EPYC 7763 (64 cores / 128 threads), torch 2.8.0+cu128 (MKL), $0.376/h. Bundle sha256 b3a8c5b0… verified on
  the box; roster 100–147 frozen there (manifest cdbdb505…); `verify --panels` ok.
* A first launch through `run_remote.sh` died instantly because I had already frozen the roster by hand and the script freezes again
  (`FileExistsError`); nothing trained. Log kept as `run.log.freeze-collision`.
* Second launch: `wave --parallel 48`. Measured 500 updates in 225–250 s and 1,000 in ~452 s per seed (≈ 2.2 updates/s in the cheap 16-line
  phase; the Mac does ≈ 18). Every seed would have hit the registered 1,500 s cap near update ~3,000. Micro-benchmark (batched attention
  forward+backward, one thread): Mac 6.7 s; box idle 22 s; box with 48 jobs 170 s → memory-bandwidth contention, not a core-count problem.
* Action: all workers killed at ≈ update 1,000–1,500. **No checkpoint was scored, no panel result exists for any roster seed.** This is the
  preregistered infrastructure failure ("the box was too slow"). Logs copied back (`remote-wave-1-ABORTED/aborted.tgz`, sha256 1050f3d9…, verified
  against the remote file) and the box destroyed; instance list confirmed empty. Cost ≈ $0.12.
* Recovery: the same roster 100–147, same frozen bundle, run on the Mac (torch 2.14) in batches from a fresh extraction. The remote x86 population
  therefore contains no results; the Mac population is the only one.
