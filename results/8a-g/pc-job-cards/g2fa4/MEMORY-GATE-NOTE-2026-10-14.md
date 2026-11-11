# G2f-a4 memory gate: what the number means (declared 10-14 about 5:45 PM ET, BEFORE trace A is evaluated and before any torch peak number exists from the PC)

## What was seen (shown, from the Mac's read of the live run, 5:31-5:36 PM ET)
- Whole-card memory in use 15,490-15,580 MiB of 16,303 (the desktop alone uses 951 MiB) from the first minutes; the supervisor's trace A gate is 12,288 MiB on that whole-card number, so it will read FAIL at update 300.
- Speed settled at 2.2 s per update (the 4090 measured 2.12 s): no sign of a slow-down from spilling into system memory. Loss falls (44.4 at update 1, 9.24 at update 50), no NaN.

## What I think it means (inferred, not shown)
The card is full because PyTorch's allocator keeps freed blocks as cache and fills the free memory; on Windows `expandable_segments` (which `local_runner.py` sets with setdefault) is not supported, so the default allocator is used and varying micro-batch widths fragment it. The whole-card number therefore measures "how much the cache grew", not how much the run needs. The 4090 measured the needed amount with torch's own counter: **8.77 GB peak allocated at accum 4** on this code and pool (`GPU-RUN-2-2026-10-14.md`); the 12 GB figure in my speed report ("fall back to 8 if the PC trace peaks above 12 GB") meant that peak. My supervisor used the whole-card number because it is stdlib-only and cannot read torch's counter. That is a flaw in how I turned the mark into code, found only on the real card.

## The reading used from now (declared before any torch peak from the PC exists)
- **Memory gate = torch peak allocated at most 12,288 MiB.** Evidence, all reported together: (i) 4090, same code and pool, 8.77 GB peak allocated (shown on that card); (ii) the PC run's own `RESULT.json` `peak_mem_mib` and `peak_reserved_mib` when the run ends (pending; a value above 12,288 allocated would make this reading wrong and is then reported as such); (iii) no CUDA out-of-memory and speed within 1.3x of the 4090's (shown so far: 2.2 s against 2.12 s).
- The registered whole-card reading is kept in the report as **FAIL** (15.5 GB against 12.3 GB), beside the reading above. Nothing is hidden.
- Not changed: no NaN/Inf, loss of updates 251-300 below 1-50, the resume match limits (0.01 / 0.02 / 0.10), the accum-32 compare limits.
- Why this is a feasibility gate and not a result mark: a wrong memory reading shows up as an out-of-memory crash or a slowdown, both visible at once; it cannot change what the run learns.

## What happens next
The supervisor stops the run at update 300 (STOPPED.txt, trace A FAIL on memory). The Mac checks that memory is the only failed item, then `clear` and starts the supervisor; the run resumes from the newest checkpoint (at most 100 updates redone). Trace A stays recorded as FAIL (whole card) in the state; the report carries both readings. Ben can overrule at any time (halt, or the registered fallback accum 8 under a new name). The accum-32 compare cannot run beside this run (the card is full): it runs on a rented 4090 (both accums on the same host) or on the PC after the main run.
