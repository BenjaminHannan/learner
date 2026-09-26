COMMON RULES: follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md (the thought-memory thread, "Memory for its own thoughts", Claude, wrote this task on 2026-09-26). Report in your final reply: each step's outcome first, integer counts, every deviation.
PLACEMENT: after 170-rv390-358i2-pc. The director may renumber it.
GPU: yes (BensPC; one job at a time; $0, no rental). Create C:\Users\benja\GPU-BUSY.txt naming rv393-pencil-pc or "queue job 175-rv393-pencil-pc" while you run and delete it at the end; if it already exists naming another job, stop with BUSY and run nothing.
WHERE: you run on the Mac. BensPC (Windows, RTX 5070 Ti) is reached from the Mac with `ssh benspc` (PowerShell, or git-bash for sha256sum/tar). Every BensPC command below runs ON BensPC over that ssh; stream the tree with `git archive ... | ssh benspc "tar -x -C <folder>"`; copy results back to the Mac worktree with scp. Never look for BensPC paths on the Mac itself.
TIME CAP: 3 h in total. Label: rv393-pencil-pc. No installs, no model downloads, no GLM or network calls. This job FINE-TUNES copies of four small nets (6.4M weights each); the new weights stay on BensPC and are never pushed.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox or origin/main already has artifacts/claude-rv393-20260926/run/.

YOUR TASK: builder for rv-393 (pencil marks) on rsn-358i2's four loop nets. The thought-memory thread wrote and sealed all code, marks and puzzles. Run it and never edit it. If something breaks, stop and report the exact error; do not patch. Do not compute any marks: the thought-memory thread counts and verifies.
READ FIRST (origin/main): artifacts/claude-rv393-20260926/PLAN.md.
Python on BensPC: C:/Users/benja/lis300/venv/Scripts/python.exe (torch CUDA + numpy). Report `python -c "import torch;print(torch.__version__, torch.version.cuda)"`.
1. On BensPC: `git archive origin/main scripts artifacts/claude-rv393-20260926 artifacts/claude-rv390-20260926/day artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt artifacts/claude-rv391-20260926/critic/train artifacts/claude-rsn358i-20260926/tests`, extract keeping paths into a fresh folder C:/Users/benja/rv393/. Check `nvidia-smi` (free memory and processes) and free disk (stop if under 5 GB).
2. SEAL: every line of artifacts/claude-rv393-20260926/SEAL.sha256.txt (19) must match (sha256sum -c under Git Bash). Anything else: stop.
3. SELFTEST: python -B scripts/claude_rv393_pencil.py selftest must print "selftest ok"; otherwise stop.
4. NETS: for s in 1 2 3 4, the sha256 of C:/Users/benja/premonition-models/rsn358i2/loop-s$s/final.pt must equal the loop-s$s line of artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt. Read the nets in place; never copy or push them. A mismatch or missing file: skip that seed and say which. Fewer than 3 seeds left: stop.
5. RUN all four nets at once, each process logging to its own file, launched detached:
   mkdir -p artifacts/claude-rv393-20260926/run
   for each s: python -B scripts/claude_rv393_pencil.py all --ckpt <net s> --seed $s --wdir C:/Users/benja/premonition-models/rv393 --out artifacts/claude-rv393-20260926/run > artifacts/claude-rv393-20260926/run/log-s$s.txt 2>&1
   Each run skips any step whose output file already exists, so a stopped run can be resumed by the same command. At 2 h 50 min, stop what is running by exact PID and push what exists (say which runs finished; a log's last line reads "all done sN" when that net finished).
6. Write artifacts/claude-rv393-20260926/run/SOURCES.txt: each net's path and sha256 as checked in step 4, GPU name, torch and CUDA versions, minutes per net, and the list of files under C:/Users/benja/premonition-models/rv393/ with their sizes (the fine-tuned weights stay there; never push them).
7. Copy artifacts/claude-rv393-20260926/run/ to the Mac worktree, then remove C:/Users/benja/rv393/ by exact path and confirm it is gone. Keep C:/Users/benja/premonition-models/rv393/. Delete the GPU-BUSY.txt you created.
PUSH: artifacts/claude-rv393-20260926/run
8. Final reply: which seeds ran, and for each seed the last 6 lines of its log as printed. Every deviation.
