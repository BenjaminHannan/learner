# dl-11 ADDENDUM-1 (written 2026-09-27T13:07:06Z from `date -u`, after the seal 57f2bd620 and before any run)

No sealed file changes, and the marks are unchanged.

1. **New Q TEST seed.** While checking the generator I printed the first 8 expressions of Q TEST seed 2991. They are
   code-made, and no model saw them. The Thread manager asked at 12:53 UTC for a fresh seed. The run therefore goes
   through the new launcher scripts/claude_dl11_run.py:
   - it runs the sealed claude_dl11_router.py unchanged;
   - it sets the Q TEST seed to 2981;
   - it drops those 8 seen expressions from the new draw (1 of them is among seed 2981's first 400).

   Seed 2991 is recorded as seen and is not used.
2. The CPU probe that set Q's size used dev seeds only (71234, 71299, 71777 and a random.Random(5) draw), never a
   TEST, day or pool seed of the run.
3. The Director granted one Luna slot, one call at a time, at 12:53 UTC. The Luna job drops to zero if limit errors
   show up. BensPC has been unreachable since 12:30 UTC. The GPU job stays in held/ for the Director's order.

Sealed with SEAL-ADD-1.sha256.txt.
