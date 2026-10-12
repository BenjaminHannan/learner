# Addendum A16 (8:50 PM ET 10-11): GW-P8 moves to Ben's Mac

Written before the Mac runs start. It changes where GW-P8 runs and how Before is scored, not the method or any pass mark of A15.
The plan file (/mnt/project-files/game-world/PLAN-AND-MARKS-2026-10-10.md) is unreadable tonight, so this addendum lives in git;
its commit time is the seal. It is copied into the plan, with a SEAL.txt line, once the shared folder works again.

## Why
- /mnt/project-files has returned I/O errors in this cloud box since about 8:20 PM ET. Both GW-P8 runs crashed when saving
  night 1 (`OSError: [Errno 5]` in the checkpoint save). Nothing they made was saved.
- Ben (8:40 PM ET): "Why not just do it on my Mac? That would be worlds faster."

## What counts
- GW-P8 = the two runs made on Ben's Mac by `game/mac_gwp8.sh` (seeds 200 and 201): the A15 command (`--keep-awake-only --keep guess
  --picker sample --quiz-picker sample --night pg --nights 8`), game code identical to commit 4fb211347 (the script checks this),
  the same parents (sha256 200: 22f70906..., 201: edbd1ee4...) and the same skills data (train.jsonl sha256 010af671...).
  The parent fingerprint was also checked by behaviour: the restarted cloud run found the same T0 (19.691660968372133) as GW-P s200.
- The cloud restart of seed 200 (local disk) is a spare. It is used only if a Mac run does not finish, and the report says so.
- Torch threads per run: half the Mac's performance cores. Thread count changes speed, not the method.

## Scoring (all on the Mac, sealed maps 7,000,000-7,000,099)
- Before = the parent at the Mac run's own T0, re-scored on the Mac, 100 maps. Q-1 uses this same-machine Before. Reason: CPU
  arithmetic differs a little between machines, so the sampled moves can differ; scoring Before and After on one machine keeps
  the pair fair. The cloud Before (3.75 / 3.61) is reported next to it as `before_T0_cloud`.
- After = night 8's checkpoint with its own temperature, 100 maps. Nights 1-7 on 50 maps (night 0 = Before, night 8 = After).
- PPO (Q-2) = the PPO checkpoint at the first saved step at or above the run's game moves (practice + quiz), scored on the Mac both
  ways (top move and sampling); Q-2 uses the stronger one.
- Audit and analysis as in GW-P (`game.audit`, `game.analyze` with `--extra-diff` against GW-P, GW-S3, GW-S, PPO top move,
  cloud Before and greedy Before).

## Marks
Unchanged from A15: Q-1 After - Before >= +1.0 with interval low > 0 (proved wrong if < +0.5 on both seeds); Q-2 at least as good as
the stronger PPO at equal moves; Q-3 wood pickaxe on >= 10% of maps; GW4 and GW5 as in sec. 4.

## A16b (9:58 PM ET 10-11): the Mac is slower, so both machines run
- Shown: the Mac's first steps took 2.4x longer than the cloud spare's (diary 405 s vs 171 s; night-0 quiz at 897 s vs 540 s).
  My 3x-faster guess was wrong. Cause not known yet (a read-only check is asked of the Mac).
- Seed 201 now also runs on the cloud box (local disk, same command, parent sha edbd1ee4...), next to the seed 200 spare.
- Rule, fixed now and not tied to any score: GW-P8 = the first machine whose two seeds both finish all 8 nights. That pair is
  scored and judged on that machine (cloud Before = the existing before-T0 files, whose T0 the cloud runs reproduce exactly).
  The other pair, if it finishes, is reported next to it as a same-seed repeat on other hardware, not as extra seeds.
  When this was written, the cloud s200 spare had logged its night-1 quiz; its value was not looked at.
