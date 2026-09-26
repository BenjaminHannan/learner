# ip-1b: the two fixes ip-1 called for, re-accepted (Fix-sleep thread, 2026-09-26)
Registered when this file is committed, before the run. An engineering acceptance test, not a learning claim.

## Why
ip-1 (registered FAIL; RESULTS.md and VERIFY.md in artifacts/claude-ip1-20260926/) showed the night is safe to kill at
every moment, but found two defects: (1) live answers slowed from 2.3 s to up to 40.1 s while a night ran on the same
CPU; (2) the fingerprint check missed 2 of 12 times on unchanged files. Fixes, both in the new file
scripts/claude_ip1b.py (claude_night_proc and claude_night_interrupt unchanged):
1. LiveGate: every user message first stops a running night (stop_night: SIGTERM, SIGKILL after 2 s), then is
   answered. This is Ben's rule (sleep only while dormant, interruptible at any time) applied on the live path.
2. fingerprint_close: the same top-5 token ids at every probe and every log-prob within 0.02 (a different adapter moved
   probe logits by 5.1 in night-proc's acceptance).
Two fixes are re-accepted together because this is plumbing, not a causal claim.

## Run (as ip-1, CPU, plain MiniCPM5-1B @87179e5c, panel 12, day seed 70301)
A first night; the live model loads ACTIVE and answers 3 questions (reference). Then 11 nights: 5 frozen at a stage
(train, save, record, switch, after), 6 at random times in [5 s, first-night length] (seed 90142). At that moment 3
user messages arrive through LiveGate (the first stops the night). Then a recovery night, then the gate on a fake clock.

## Marks (all must hold)
- J0 every staged night reached its stage.
- J1 after every stop, ACTIVE is the old version or (only past the switch) a complete accepted new one.
- J2 after every stop, a fresh process loads ACTIVE and its fingerprint is close to its record (fix 2).
- J3 for every mid-night message: answers byte-identical to the reference, each within 15 s end to end, stop included.
- J4 a clean night after all stops exits 0, is accepted, becomes active, and loads with a close fingerprint.
- J5 D1-D4 the dormancy gate (as ip-1).
PASS = all. Reported, not marked: exact fingerprint matches, stop times, where random stops landed, how many
messages found a night still running.

## Limits
CPU, tiny sizes, the bare 1B as the live model. Stops here use SIGTERM first (the real path); ip-1 covered SIGKILL at
every stage.
