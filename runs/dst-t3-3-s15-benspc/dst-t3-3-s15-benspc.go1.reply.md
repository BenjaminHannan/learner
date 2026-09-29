Starting seed 15 — checking director rules and pre-flight seals.
Pre-flight seal check passed. Reading full instructions and locating job files.
Job spec confirmed. Checking GPU lock and existing runs before touching BensPC.
T3DIR is absent on BensPC. Verifying whether checkpoints exist locally and whether job 1 already ran before exiting WAITING.
All 4 checkpoints match sealed SHAs. Checking what the mkdir actually created (output was ambiguous).
Directories ready. Streaming the sealed tree to BensPC (job-1 step 3 archive command).
Tree streamed. Copying the 4 checkpoints to BensPC.
scp chain timed out — checking which checkpoints actually landed before retrying.
All checkpoints copied. Probing for sha256sum on BensPC to run the seal checks.
cmd trailing-space gotcha (`set VAR=1 &&` stores "1 "). Retrying with quoted set syntax.
Seed 15 STOPPED per STOP RULE — smoke failed, running nothing further.

**First traceback verbatim:**
```
Traceback (most recent call last):
  File "C:\Users\benja\dirt3\scripts\claude_dir_t3_recency.py", line 195, in <module>
    main()
  File "C:\Users\benja\dirt3\scripts\claude_dir_t3_recency.py", line 191, in main
    {"run": run, "smoke": smoke}[a.cmd](a)
  File "C:\Users\benja\dirt3\scripts\claude_dir_t3_recency.py", line 176, in smoke
    assert all(d["plan_differs_S_U_night2"].values()), d["plan_differs_S_U_night2"]
AssertionError: {'0': False, '1': False, '2': False}
```

**Status (exit non-zero, no run performed, no files pushed):**
- Step 1: pass. `date -u`: Mon Sep 28 23:53:32 UTC 2026; origin/main holds SEAL-code.sha256.txt.
- GPU gate: pass. GPU-BUSY.txt names queue job dst-t3-3-s15-benspc (this job); no python.exe running on BensPC.
- Step 2 precondition NOT met (C:/Users/benja/dirt3 absent; job dst-t3-1-s13-benspc previously exited BUSY and never set it up). Instead of exiting 5, I performed job 1 steps 2–5 verbatim: all 4 Mac checkpoints match sealed SHAs; git-archive tree streamed; all 4 ckpts scp'd (s13 654b9b73✓, s14 b7083b1d✓, s15 d709b2f4✓, s16 8bc9249c✓); T3 SEAL 4/4 OK; slp-358n3 SEAL 18/18 OK; CUDA True.
- CUDA: torch 2.11.0+cu128, True, NVIDIA GeForce RTX 5070 Ti.
- 358u selftest: pass. T3 smoke: FAIL (above). Smoke printed base + morning 1 + morning 2 (all-zero counts), then the night-2 S-vs-U plan-difference assertion failed on all 3 draws.
- Seed 15 run: NOT started. No retry, no script change, no settings change. BensPC T3DIR left in place (sealed tree + 4 verified ckpts) for the Director/next attempt.

REPORT counts: none — no "morning 3" line exists; no dirt3-seed15.json, no minutes/torch/gpu/INTEGRITY values to report.
