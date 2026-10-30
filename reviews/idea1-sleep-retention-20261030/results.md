# Wave 1: incomplete

**Verdict: INCONCLUSIVE.** The CPU run reached the unchanged 1,050-second HF outer limit during its first update. It recorded 0 completed updates and no post-training checkpoint, so learned, kept and harm are not measurable. The control learned 3 earlier-block facts and kept 0. HF baseline general hits were 6/8, matching the control; final general hits are unavailable. Native evaluation was not run: there was no completed phase, and the archived native path requires an adapter export, which was prohibited.

The CPU run started with 12.65 GiB available; just before training it had 9.66 GiB and pressure level 1. Its minimum sampled availability was 8.13 GiB, maximum pressure level 1, and peak sampled process RSS 3.84 GiB. Both owned processes exited. The earlier failed launch briefly loaded the model on the Mac GPU because the archived backend automatically selected MPS; its CPU assertion stopped it before baseline or training. The second launch explicitly forced CPU before loading. No adapter was exported or promoted.

**For Ben**

- **Shown:** The old control learned 3 earlier facts and later kept 0.
- **Shown:** This run started with 6 of 8 general answers correct, just like the control.
- **Shown:** The CPU run ran out of its fixed time before completing its first update.
- **Suggested:** This Mac CPU setup is too slow for this particular fixed-budget test.
- **Untested:** Whether re-studying old cards prevents forgetting or harms general answers.
