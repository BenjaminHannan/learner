# 0.2d gates ADDENDUM 2 (Month-end, 2026-09-26 ~15:00 UTC)

02d-gates-2026-09-26.md is unchanged. Slot 6 (answer fixes) gets one memory-path candidate beside y1f: wc-02d, whole-chat
reading (Benchmarks' proposal after bm-398d: plain 1B on the whole chat 109 vs store top-20 88 of 297). One change: when the
user's chat history fits the 1B's context, the memory path reads the whole chat instead of the store's top 20. Benchmarks
writes, seals and runs it on its own budget, base X' (lis-319 via claude_readersha_wrap). Its marks must include Y1 on a
blind bank, H3 (never-told "don't know") not worse by more than 2, and ms per turn reported. If wc-02d and y1f both pass
by 09-29 12:00 UTC, the one with the higher Y1 joins; they are never joined together in 0.2d without their own combined test.
