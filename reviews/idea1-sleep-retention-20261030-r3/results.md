# Wave 1 r3: incomplete

**Verdict: INCONCLUSIVE.** macOS reported no space left on the system volume while saving during phase 1. Five updates were recorded, but no post-training checkpoint was completed. The retention verdict and HARM cannot be scored. The baseline was 6/8 general hits; the three later checkpoints are unavailable.

| Block | Fact answer | Learned after own block | Kept after block 3 |
| --- | --- | --- | --- |
| 1 | Copperfern | Not measured | Not measured |
| 1 | Moonhaven | Not measured | Not measured |
| 1 | Sunwillow | Not measured | Not measured |
| 2 | Mistbrook | Not measured | Not measured |
| 2 | Pinecrest | Not measured | Not measured |
| 2 | Starmeadow | Not measured | Not measured |

| Checkpoint | General hits |
| --- | --- |
| Baseline | 6/8 |
| After block 1 | Not measured |
| After block 2 | Not measured |
| After block 3 | Not measured |

The process ran for 37.6 seconds; baseline finished 25.0 seconds after process start. The first update took 2.34 seconds, setting the phase watchdog to 176.2 seconds (24 × first step + 120 seconds); it did not expire. The total cap was 1,800 seconds. Starting available memory was 11.01 GiB, the minimum sampled was 5.99 GiB, and the maximum pressure level was 1. Peak sampled process RSS was 0.58 GiB; this does **not** include all GPU allocations, whose peak was not measured. The child exited and was reaped. The system volume had approximately 566 MiB available after the failure; the run's scratch files occupied only 7.2 MiB, so removing them could not safely recover enough space for a retry.

The archived control used CPU/BF16 and two threads, not MPS, and finished its HF portion in 610.7 seconds. This rerun used the real `lfm3_mps` backend (MPS/FP16), with rank 8 and the control's other test settings. The profile normally defaults to rank 16; rank 8 was explicitly set to preserve the control. Scratch data and adapters stayed separate; nothing was exported or promoted. Native evaluation was not run.

**For Ben**

- **Shown:** Before studying, the model got 6 of 8 general questions right.
- **Shown:** The computer ran out of disk space while the model was studying. We could not finish the test.
- **Shown:** In the older control, the model learned 3 earlier facts and kept 0 at the end.
- **Suggested:** The MPS setup can make training steps much faster than the earlier stalled CPU run, but this partial run cannot establish the full test time.
- **Untested:** Whether studying old cards helps the model remember them, or changes its general answers.
