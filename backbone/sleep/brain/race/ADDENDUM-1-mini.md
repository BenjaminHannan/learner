# Race-mini addendum 1 (2026-10-27 ~19:45Z; written before any treatment arm ran)

What happened (PC job, 16:53-18:57Z): the add-on control `lora_s1` (q4 base, 300 steps a night, seed 1) finished:
final C2+C4 forward recall 0.98, night-4 0.555, ARC-500 0.840 vs base 0.856, ~1180 s a night (2.05 h a run).
The validity arm `bf16_s1` (add-on on the bf16 base) ran out of GPU memory 22 s in (12.4 GiB allocated, 5.06 B-param bf16 base = 10.1 GB on a 16 GB card),
so the job stopped itself. No LoRA+ and no whole-model arm has run.

Two problems, two changes (agreed with the add-on side, which proposed the dose check):
1. **Ceiling.** At 300 steps the control already recalls 98%, so no arm can beat it by the +4 pass mark.
   The race now runs at **75 steps a night** (all arms, all seeds, and the whole-model lr scout), everything else unchanged.
   Ceiling fallback, decided from the control only: if the pooled 75-step control's final C2+C4 >= 0.90, every arm's headline becomes its night-4 C2+C4 score instead.
2. **Validity check.** The bf16 base does not fit the 16 GB card (pass marks and the bf16 arm are dropped; untested whether race-mini reproduces the q4-vs-bf16 gap).
   It is replaced by a dose check on the same packed base: the existing 300-step control `lora_s1` must beat the 75-step control `c75_s1` (seed 1) by >= 2 points
   of final C2+C4 recall, or the job stops (race-mini is then insensitive to the amount of storage training and both sides rethink).
   Prior evidence (full pipeline, q4 Week-1, work scale 0.5x/1x/2x): 25/45/59. Seed 1 only.

Also: race_mini.py caps GPU memory at $SLEEPB_CUDA_CAP_GIB (14 on the PC) so a run fails fast instead of spilling into system memory under WSL;
pc_race_mini.sh now waits for pc-jobs/handoff/GO-RACE-MINI, can pause between arm-seeds (pc-jobs/handoff/PAUSE-RACE-MINI), and ends by writing
pc-jobs/handoff/RACE-MINI-DONE. Run order: c75_s1, gate, lp16_s1, scout_qs_{1e-3,3e-3,1e-2} (75 steps), qs_s1, c75_s2, lp16_s2, qs_s2 (~35 min a run, ~5 h).

Each side's round-1 pass marks are unchanged, with "lora" meaning the 75-step control (c75) and the headline as in point 1.
