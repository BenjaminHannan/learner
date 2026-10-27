# Deviation 1 — link isolation v2 runs on a rented box instead of the Mac

Written 2026-09-20 before any registered link-isolation-v2 seed has run anywhere.

- Why: the Mac slots are taken by dispatcher v4 and the reliability population; Ben asked for cheap rental parallelism.
- Where: vast.ai instance 51781306 (Ryzen 9 7950X, CPU lane, one torch thread per job, Python 3.11 / torch 2.8.0 instead of the Mac's 3.12 build).
  The project is mirrored at the identical absolute path, so the frozen manifest (c4b931d5…) is checked unchanged by the unmodified launcher;
  `check_manifest` passes on the box.
- Speed check before launch (rule from INCIDENT-1): a throwaway NON-registered seed 9999 of stage A ran 1,000 updates in 46.5 s while six other
  jobs were running on the box (needs ≥ 7.1 upd/s to fit the 420 s budget; measured ≈ 21). Its folder was deleted; its accuracy numbers say nothing
  about registered seeds and were not used for any decision.
- Unchanged: script, manifest, seeds 1400–1402, schedule, time caps, stage-A gate, arms, marks, report. Commands are the ones queued in chain4.sh.
- Changed: machine/numerics only; two stage-B arms run side by side (six jobs) instead of one arm at a time. Each arm's wall-clock caps still apply.
- Results are copied back hash-verified. Any capped/incomplete run is reported as such, never rerun silently.

## Outcome (2026-09-20, 17:48 UTC)
Stage A ran its full 3,000 updates in 3 min on all three seeds and ended at chance (attr 79–96/512; terminal-given-true-endpoint 87–108/512). 0/3 qualified, so by the registered rule stage B did not train and the stage-B hypothesis is untested. Results copied to `remote-box-51781306/` (tarball sha256 6abe9137cffbb058…, matched on both sides; checkpoints excluded). Box 51781306 destroyed afterwards; instance list confirmed empty.
