# Run notes

## Context and pre-registration boundary

Machine: Ben's Mac, Apple M1 Pro, 32 GiB unified memory. Workspace:
`/Users/ben-hannan/.codex/worktrees/retention-isolation/beautiful-model`.
Initial inspected main revision: `2b8f67039`.
User rules received and UTC observed with `date -u`: **2026-09-27 03:47:06 UTC**.

Before those rules arrived, a written-protocol, uncommitted seed-27 reasoner
pilot was started locally. PID observed in our process listing: **90107**.
It is exploratory only, not a registered result. Only that own process was
instructed to stop; the watcher, PC and all other jobs were left alone.
Confirmed by the owning agent: started **2026-09-27 03:44:48 UTC**, SIGINT sent
to PID90107, and that PID subsequently absent. Last flushed entry was grid step
1,250/2,500; no completed phase/checkpoint or held-out score. Details are in
`reasoner/EXPLORATORY-INTERRUPTED.md`.

Ten local software unit checks passed before registration. They are development
checks, not 1B model evidence. They will run again after the marks are committed.

PASSMARKS was pushed to main as **c7c8221a0a1617ddcbfad5fc30517da86573b8e5**
before registered R1/C1. Their individual notes/logs record subsequent starts.
Usage at the first stop-threshold check: 4% used, **96% remaining**. Stop our own
work if the reported remaining allowance falls below20%; no reset/purchase.

## Registered training completed

R1's two runs used software `697f18b58057a6b4f376acc65abb5cd3e24fb5f8`:
seed 29, PID 98193, 03:55:34–04:02:38 UTC; seed 30, 04:02:58–04:10:02 UTC.
The individual RUN-NOTEs contain full PID/machine/command records. R1 is
INCONCLUSIVE because seed 29 did not meet initial grid mastery.

R2's marks and runner were committed, pulled with rebase and pushed to main as
`57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7` before launch. All 31 recorded R1
dependency hashes were unchanged, captured in `r2/RUN-CODE.json`. R2 used:

- Seed 31: PID 7633, 2026-09-27 04:13:40–04:26:02 UTC, MPS, 742.1 seconds.
- Seed 32: PID 12897, 2026-09-27 04:26:22–04:38:16 UTC, MPS, 713.9 seconds.

Both runs completed all 6,000 grid and 2,500 sum steps and passed their registered
checks. No pull/rebase or dependency edit occurred between their launches and
completion. CPU-only chat fixture repairs ran separately, with their own
date/PID records in `chat/SOFTWARE-REPAIR-RUN-NOTE.md`. The final package has
10 core, 10 chat and 4 reasoner tests passing; logs retain the earlier test
setup failure and correction. No 1B model was evaluated.

Reported usage remaining at 2026-09-27 04:37 UTC: **89%**. Neither the stop
threshold nor any reset/purchase was reached.
