# rsn-358e addendum 3: moe-grow and the same-size rule (2026-09-26 21:18 UTC, before the verdict; marks unchanged)

**Why:** the Thread manager's review at 21:18 UTC. ADDENDUM-1 said moe-grow "breaks the same-size rule", but ADDENDUM-2 made it the one graded arm without saying what that means for a PASS.
**Already seen when this was written:** moe-grow's after-A and after-B dev scores (sent to the Thread manager at 20:21 UTC). Dense and moe have not been read. The marks do not change.

**(1) Exact weight counts** (small nets, counted from the code with scripts/claude_rsn358e2_arms.py make_net and grow):

| net | total weights | trainable in that phase |
|---|---|---|
| dense (the loop control) | 1,646,750 | all |
| moe | 1,650,342 | all |
| moe-grow, phase A | 1,650,342 | all |
| moe-grow, phase B (F is measured here) | 2,705,070 | 1,054,728 (the 8 new experts and 8 new router rows) |
| moe-grow, phase C | 3,759,798 | 1,054,728 |

- So after growing, moe-grow has 1.64x the dense control's weights, and 1,058,320 more.
- result.json's "weights" field for moe-grow reads 1,650,342. That is the count at the start, not after growing; the verdict must say so.

**(2) What a PASS means.** A PASS on the current marks is **not** a PASS under Ben's same-size rule. It would be registered as "PASS on forgetting, with a bigger net (1.64x total weights at phase B); not same-size". It could not be used to claim that experts beat a same-size dense loop, and it would not count toward any same-size comparison. A FAIL needs no caveat to be read as a FAIL; the verdict still carries the size line.

**(3) A same-size version, stated now and not run:** moe-grow-eq.
- All 12 experts exist from the start, each with hidden width 4d/12, so total weights equal the dense MLP (plus the router), as in moe.
- Phase A: only experts 0-3 can be routed to (router rows 4-11 masked). Phase B: 0-3 frozen with everything else from A, 4-7 unmasked and trainable. Phase C: the same with 8-11.
- Same seeds, data, steps and marks as moe-grow (PASSMARKS.md with F_moe-grow-eq), graded against the same dense control.
- It is sealed only if it is run, and only after the 358e verdict is registered. If moe-grow fails, the replay change (NEXT-replay-draft.md) comes first, and any replay test at equal size uses this layout.

**Diagnostic status:** claude_rsn358e_diag.py writes the REPRO check, the byte compare and the M0/M1/M2 masks together into one diag.json. At 21:18 UTC it is in phase B (seed 1 at step 1,750 of 2,500), and its losses match the stage-1 runs step for step so far.
