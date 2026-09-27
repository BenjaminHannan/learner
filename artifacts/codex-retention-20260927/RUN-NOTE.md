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
