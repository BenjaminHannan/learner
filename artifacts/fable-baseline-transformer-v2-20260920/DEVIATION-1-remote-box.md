# Deviation 1 — arms run on a rented box (written 2026-09-20 before any remote arm ran)

State: arm I1-H1 (seeds 1200–1202) has completed on the Mac (torch 2.14, Apple CPU). At Ben's instruction to parallelise on a cheap rental, the remaining arms run on vast.ai
instance 51781306 (Ryzen 9 7950X, torch 2.8.0 CPU, one thread per job, the project mirrored at the same absolute path, hash-frozen files verified there by the same
FREEZE.sha256). Measured before launch with dev seeds ≥ 990201: 9.1 updates/s for one job, 5.8 with six jobs (Mac: 6.4–6.8), so six jobs fit the registered 1,200 s cap.
* Wave R1: I0-H1 + I1-H0 (six jobs). Wave R2: I0-H0 + a REPLICA of I1-H1 (six jobs). The replica tests whether machine/torch version changes the outcome; the Mac I1-H1
  result stays the registered one for that arm and the replica is reported beside it, never merged.
* Caveat disclosed: the "same random draws across the two init arms of one seed" property is guaranteed within one machine; across Mac and box it holds only if torch's CPU
  generator is stable across versions/platforms (the replica checks the practical consequence).
* The GPU on the box is NOT used for registered arms (a generic CUDA launcher works at 25.7 updates/s for one job, but it changes the init generator and collapses to
  4.2/2.1 updates/s per job with 3/6 concurrent jobs).
* Mac queue: the remaining baseline arms were removed from the Mac chain so nothing runs twice into the same folder.

Launch incident (2026-09-20): the first remote launch used bash; `run_wave_v2.sh` is a zsh script (zsh array for the seeds), so bash started only seed 1200 of I0-H1 and
I1-H0. Both jobs were killed after ~1 minute, before any fit scoring; their folders were moved aside on the box (`/workspace/aborted-bash-launch`). zsh was installed on the
box and the identical, unmodified `run_wave_v2.sh` relaunched under zsh. No result was seen from the aborted jobs.

Outcome note (2026-09-20): all 12 box runs completed 6,000 updates inside the 1,200 s cap (967–995 s). Results are stored separately in `remote-box-51781306/`
(tarball hash-verified on both sides), never mixed into the Mac's `I1-H1/` folder. The box's I1-H1 replica did NOT reproduce the Mac seed-for-seed:
seeds 1200/1201 pass 512/512 ×4 on both machines, but seed 1202 passes on the Mac and sits at chance on the box. So a "seed" does not fix the outcome across
machines (different torch build/CPU numerics), and the I0-H1 / I1-H0 / I0-H0 arms (box only) are comparable to the box's I1-H1 replica, not seed-for-seed to the Mac's.
