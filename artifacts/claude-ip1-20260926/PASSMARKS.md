# ip-1: sleep only while dormant, and interruptible at any moment (Fix-sleep thread, 2026-09-26)
Registered when this file is committed, before the run. An engineering acceptance test, not a learning claim.

## Why
Ben (14:49 UTC 09-26): "sleep should just be while it's dormant, and be interruptible at any time", before overnight
learning ships to anyone's copy. The night already runs as a separate process with versioned adapters and an atomic
ACTIVE pointer (scripts/claude_night_proc.py, acceptance PASS 6/6), but that acceptance killed one night at one moment.

## Code
scripts/claude_night_interrupt.py: the dormancy gate (Dormancy, stop_night) and the test harness. The code under test,
claude_night_proc.train_child, is unchanged; the harness only adds hooks in the child that freeze it at a stage.

## Run (CPU, plain MiniCPM5-1B @87179e5c, panel cut to 12 items, one day of 4 puzzles with one checked answer each)
1. A first night, unkilled, makes v0001 active and times a whole night (T seconds).
2. The live assistant loads ACTIVE once and answers 3 fixed questions (16 new tokens, greedy) as the reference.
3. Eleven nights are killed by exact PID (SIGKILL): one frozen at each stage (train: after the first optimizer step;
   save: candidate .pt temp file half-written; record: .pt in place, .json record not written; switch: new ACTIVE
   temp written, not renamed; after: ACTIVE switched, night not exited), and 6 at random times in [5 s, T]
   (seed 90141). Just before each kill and after it, the live assistant answers the 3 questions again.
4. A clean night after all kills (recovery). 5. stop_night on a running night. 6. The gate on a fake clock.

## Marks (all must hold; the script computes them)
- I0 every staged kill reached its stage (else that moment was not tested).
- I1 after every kill, ACTIVE names the old version, or (only if the night got past the switch) a new version whose
  .pt and accepted .json record both exist. Never a missing or half-written file.
- I2 after every kill, a fresh process loads the active version and its behaviour fingerprint equals its record's.
- I3 during and after every kill, the live assistant's answers are byte-identical to the reference, each within 15 s.
- I4 a clean night after all kills exits 0, is accepted, becomes active, and loads with a matching fingerprint.
- I5 stop_night (SIGTERM, SIGKILL after 2 s) stops a running night within 3 s.
- D1 no night starts before 600 s without user activity; D2 one starts once 600 s have passed; D3 activity while a
  night runs stops it at once, and the next night needs a new full idle period; D4 never two nights at once.
PASS = all. Otherwise FAIL.
Reported, not marked: where each random kill landed, leftover temp files and orphan .pt files (ignored by loaders by
design), live answer times, load times.

## Limits
CPU and tiny sizes; the live assistant here is the bare 1B, not the joined agent (Month-end can add a joined row).
SIGKILL is the hardest stop; a power cut can also lose the OS write cache (not tested; writes are fsynced before rename
for records and ACTIVE, and torch.save's temp file is renamed only after it is complete).
