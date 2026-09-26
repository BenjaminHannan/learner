# y1t addendum 1: run on BensPC, not a rental (Answering-from-memory thread, 2026-09-26 18:51 UTC, before any y1t run and before the practice chats exist)

**Why:** Ben, 18:42 UTC (relayed by the Thread manager, 18:48): the vast money is gone; BensPC is the default and CPU
is free. handoff/held/rent-0y1t.md is never released; handoff/held/benspc-y1t.md replaces it.

**What changes:** the machine only (RTX 5070 Ti 16 GB, torch 2.11, Windows) and so the wall time. The code, seals,
seeds, data, decision rules, proved-wrong clause and predictions in PLAN.md are unchanged. The plain 1B's DEV run is
still on the same machine as the trained model's (PLAN step 5), so the comparison stays like for like.

**What it means:**
- bm398r's trainer uses no autocast, so the torch 2.6/2.8 autocast weight-cache bug (MEMORY: AUTOCAST BUG) does not
  touch it on either machine.
- y1g's own DEV reference (A1 26 / 24 / 2) came from a rental. It stays report only; the verdict uses this run's rows.
- BensPC runs one job at a time, so y1t waits for the job before it (claude-sleep-358i2pc) and for the data gate
  (GATE-data.md).
- The step 6b rows for the Wrong-answers-stated-as-fact thread's y1t-H1 marks run on BensPC too; that thread's $0.20
  is not spent.
