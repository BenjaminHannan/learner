# Custom IO jobs on Ben's own machines (BensPC 5070 Ti and the M1 Pro)

From the custom reader/talker thread, 2026-10-05 about 11:40 UTC (7:40 AM ET). Ben's rule (11:20 and 11:22 UTC): run on
his RTX 5070 Ti whenever it can, several jobs at once, use the M1 Pro too, and rent Vast only when both are full.
The ultracode blocker thread shares the 5070 Ti. Nothing here touches GOLD-PRIVATE, reserved or blind panels, and no
checkpoint is ever deleted.

Branch: `claude/custom-reader-talker-4x309r` (code: `custom_io/`). Curriculum: `skills_curriculum/` from branch
`claude/project-thread-y0sxwe` (pure Python, builds the seed-1 200k skills data; hashes are checked).
Runner: `custom_io/local_runner.py` (Python only, no bash needed on Windows; read its docstring).

## 1. Stage the code (on the Mac)
```
git fetch origin claude/custom-reader-talker-4x309r claude/project-thread-y0sxwe
mkdir -p ~/custom-io/src && cd ~/custom-io/src
git -C <your learner checkout> archive origin/claude/custom-reader-talker-4x309r custom_io | tar -x
git -C <your learner checkout> archive origin/claude/project-thread-y0sxwe skills_curriculum | tar -x
```
Copy `~/custom-io/src` to the PC as `C:\Users\benja\custom-io\src` (scp -r). Later updates: same two commands, then
re-copy; a queue already running keeps its own frozen copy of the code.

## 2. Build the data once per machine (about 5-10 min, CPU only)
PC (PowerShell, in `C:\Users\benja\custom-io\src`, with the Python env you used for the fix screens, torch 2.11 cu128):
```
python -m custom_io.local_runner setup --work C:\Users\benja\custom-io\work --curriculum .
```
Mac (in `~/custom-io/src`): `python3 -m custom_io.local_runner setup --work ~/custom-io/work --curriculum .`
It must print `setup ok` (both builds hash-checked). If it stops on a hash mismatch, stop and tell the thread.

## 3. Run the queues
**First, PC queue 32 (added 12:55 UTC, 8:55 AM ET): the B2 screen, 2 runs at once.** Same launch as queue 30 below, with
`custom_io\queue_local\32-pc-b2-screen.txt`, `--par 2` and stdout to `C:\Users\benja\custom-io\work\q32.log`. Start
queue 30 after it (or alongside it if nvidia-smi shows room for more runs; each run gates on its own free memory).

PC queue 30 (pythia-31m lr pick, then plain_tf and plain_tf_steps on seeds 200-202; 9 runs, up to 3 at a time).
Launch it detached the way you launched the fix screens, so it survives the ssh session ending:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\30-pc-baselines.txt --device cuda --par 3 --busy C:\Users\benja\GPU-BUSY.txt
```
with stdout to `C:\Users\benja\custom-io\work\q30.log`. Each run starts only when nvidia-smi shows its memory free
(5-6 GB per run), so it waits while the blocker thread's jobs fill the card and never stops them. It adds one line per
running run to GPU-BUSY.txt and removes only its own lines. If your convention for the blocker queue treats any existing
GPU-BUSY.txt as "busy, don't start", pass `--busy C:\Users\benja\GPU-BUSY-custom-io.txt` instead so both threads can run.
To yield the card: create `C:\Users\benja\custom-io\work\STOP` (running runs finish, no new ones start); delete it and
re-run the same command to resume (finished runs are skipped).

Mac queue 31 (speed probes, about 15 min, then 8-shot pythia-31m and SmolLM2-135M on the dev splits, no training):
```
nohup python3 -m custom_io.local_runner run --work ~/custom-io/work --queue custom_io/queue_local/31-mac-probe-fewshot.txt --device mps --par 1 > ~/custom-io/work/q31.log 2>&1 &
```
The hf lines download pythia-31m (about 120 MB) and SmolLM2-135M (about 270 MB) from the Hugging Face hub; they need
`transformers` (any recent version) in that Python env.

## 4. Send results back
When a queue ends (and, for the PC queue, once after the first 3 runs end), copy `work/results/<queue>/` WITHOUT
`checkpoint.pt` files into a checkout of `claude/custom-reader-talker-4x309r` at `custom_io/results/<queue>/`, commit
("Custom IO: results of queue NN from BensPC / M1"), pull --rebase and push to that branch. Keep every checkpoint.pt on
the machine where it was made (never delete). Add one LIVE.md line per start and finish as usual. If a run fails, its
`stdout.events.txt` and `rc.txt` are in its folder: push those too, the thread will fix and requeue.
