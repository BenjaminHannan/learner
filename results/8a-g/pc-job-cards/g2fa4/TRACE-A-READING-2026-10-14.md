# G2f-a4 trace A: what failed, what I decided, and how the run will be judged (written 10-14 about 5:55 PM ET, BEFORE any card-noise measurement exists)

## Trace A as registered (read by the supervisor 5:48:16 PM ET, run stopped 5:48:20 PM)
| item | limit | seen | verdict as registered |
|---|---|---|---|
| no NaN/Inf | none allowed | none | PASS |
| loss falls | mean(251-300) below mean(1-50) | 2.574 vs 17.636 | PASS |
| memory | 12,288 MiB, whole card | 15,757 MiB | **FAIL** (see MEMORY-GATE-NOTE) |
| resume, first redone update | within 0.01 | 0.0 (update 101 exact) | PASS |
| resume, mean absolute difference over the 50 redone updates | at most 0.02 | 0.0167 | PASS |
| resume, largest single difference | at most 0.10 | 0.1191 (update 147: 3.4866 vs 3.3675) | **FAIL** by 0.019 |
The two resume limits (0.01 / 0.02 / 0.10) were mine, set on 10-14 from the CPU test, not big-run's. Nothing below changes a registered verdict: both FAILs stay on record.

## What the resume numbers look like (shown by the Mac, 5:48 PM)
Redone updates 101-107 differ by at most 0.0002 (101 exactly 0); 108-121 up to 0.006; 122-139 up to 0.034; 140-147 up to 0.12; 148-150 back under 0.04. Suggested, not proven: tiny GPU rounding differences (bf16, kernel choice after a restart) that grow while the model is still changing fast. A broken restore of the optimizer, the random streams or the data position would already differ at update 101, and 101 is exact. The CPU test of the same code showed the same kind of drift on the PC's CPU, smaller.

## Decision (mine as owner of the pack, 10-14 about 5:55 PM ET; Ben can overrule at any time)
The registered fallback (accum 8, new name) answers a memory or recipe problem. It would not remove GPU rounding noise (the noise is independent of the accum), so it is not a response to the resume item, and the memory item is the cache-fill reading in MEMORY-GATE-NOTE. So: **resume the run now from the newest checkpoint (step 300, nothing redone), and gate the READING of its result, not its running.** A stop costs 15 h of card time if wrong, a restart costs minutes. Before the restart the Mac copies step-200.pt and its sidecar to `work\g2fa4\ckpt-keep\` (copy, not move), because the overlay keeps only the newest two and a restart rotates step-200 away.

## How the run will be judged (declared now, before the probe exists)
The run is read (marks B3G2-1..7, thinker rounds at inference, stop-head accuracy) only if ALL hold:
1. **Memory:** RESULT.json `peak_mem_mib` (torch peak allocated, whole run) is at most 12,288. Above that, the memory reading in MEMORY-GATE-NOTE is wrong and the run is reported as such.
2. **Resume probe (card noise):** from the kept step-200.pt, run the same job twice (R1, R2) for 50 updates (201-250) on an idle card, and compare each with the continuous updates 201-250 already logged by the run (C). With n = largest |R1 - R2| over the 50 updates and d = largest |R_i - C| over i = 1, 2: **PASS if d <= max(0.10, 3n)**; FAIL otherwise (the resume then differs from continuing by more than the card's own run-to-run noise: the restored state is wrong somewhere, and the run is not read). If R1 and R2 are bit-identical (n = 0) the limit is the original 0.10 on d. The probe needs the card idle (about 10 min); it runs after the main run, or earlier if Ben halts or the card is free.
3. **Compare:** the accum-32 baseline compare (300 updates, same seed and rows) still decides whether the run is read, as registered. It cannot run beside the main run (the card is full); it runs on a rented 4090 (both accums on the same host, in the same box as the speed sweep if the box plan allows) or on the PC after the main run. PASS or UNCLEAR reads as GO; FAIL means do not read.
4. Loss, NaN and the first-update resume item already PASS and stay as they are.
If 1 or 2 fails, the 15 h are not lost as science (the run's loss curve and speed stand) but the result is not read as a G2f-a4 readout, and the registered fallback (accum 8, new name) is re-opened with Ben.

## What is NOT claimed
That the resume is correct on GPU (suggested only); that the card never spilled (shown only for the first minutes: 14,346 MiB dedicated, 82 MiB shared); that accum 4 trains like accum 32 (untested until the compare).
