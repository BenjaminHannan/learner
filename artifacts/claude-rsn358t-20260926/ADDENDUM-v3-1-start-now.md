# 358t v3 addendum 1: start before 358i2's verdict (2026-09-26 18:42 UTC, before any v3 run)

**Ben's decision:** at 18:39:52 UTC he wrote to the Thread manager (cmsg_01FuvegZXjMmeUzStiEFVnEWVCf81aGiBZ8MSRwbKQBw7t): "What's the progress been you can choose to spend money". The Thread manager relayed approval of up to $1.60 for 358t v3 and asked for the fastest route to both verdicts.

**Change:** PASSMARKS-v3.md's order rule ("v3 runs only after rsn-358i2 reports") is lifted. That rule was about value, not validity. Nothing in v3's marks depends on 358i2:
- G0-G5 compare against 358i's plain, and V0 uses v3's own gradient log.
- If 358i2 later proves the cache suspect wrong, v3 still tests the TRM schedule and loop8 on code whose layers train.

The marks, code and seal are unchanged.

**Added builder gate (task file only, no code change):** on the rental, Stage 0's line "loop  free=3 grad=2 cache=False" must end in 0/12. If it doesn't, the fix does not work on CUDA: stop before training and spend nothing more. This is the CUDA check the CPU result could not give.
