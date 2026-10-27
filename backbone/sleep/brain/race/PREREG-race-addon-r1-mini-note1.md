# Note 1 to PREREG-race-addon-r1-mini.md (05b7b2f9...), sealed before any 75-step run

Follows race-mini ADDENDUM-1 (sha 37937ea2..., commit 63cfa297b3 on claude/project-thread-qcuhwj), agreed by both sides 19:35Z Oct 27:
the first attempt's 300-step control reached 0.98 final C2+C4 (night 4 0.555), so no arm could show +4, and the bf16 validity arm ran out of memory.
- All arms run at 75 steps a night. "lora" in my PREREG now means the 75-step control c75 (same seeds and batches); my arm is lp16 at 75 steps.
- Validity: the existing 300-step lora_s1 must beat c75_s1 by >= 2 points of final C2+C4 (else the job stops, nothing scored).
- Ceiling fallback, decided from the control alone before looking at lp16: if pooled c75 final >= 0.90, the headline for every arm is night-4 C2+C4.
- Pass / harm / wrong marks unchanged: pooled lp16 >= c75 + 4 and p < 0.05 and each seed lp16 >= c75; harm ARC < base - 5; wrong if lp16 <= c75 + 1.
