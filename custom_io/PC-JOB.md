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
Updated 14:45 UTC (10:45 AM ET). Queue 32 (B2 screen) is done on the cloud: skip it.

**PC queue 33 first: the B2 confirm** (B2, plain_tf and plain_tf_steps on seeds 200-205; 18 runs, up to 3 at a time).
Launch it detached the way you launched the fix screens, so it survives the ssh session ending:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\33-pc-confirm-b2.txt --device cuda --par 3 --busy C:\Users\benja\GPU-BUSY.txt
```
with stdout to `C:\Users\benja\custom-io\work\q33.log`. Then PC queue 30 (pythia-31m lr pick, 3 runs), same command with
`30-pc-baselines.txt` and `q30.log`; it can run alongside 33 when nvidia-smi shows room. Each run starts only when
nvidia-smi shows its memory free (5-6 GB per run), so it waits while the blocker thread's jobs fill the card and never stops
them. It adds one line per running run to GPU-BUSY.txt and removes only its own lines. If your convention for the blocker
queue treats any existing GPU-BUSY.txt as "busy, don't start", pass `--busy C:\Users\benja\GPU-BUSY-custom-io.txt` instead
so both threads can run. To yield the card: create `C:\Users\benja\custom-io\work\STOP` (running runs finish, no new ones
start); delete it and re-run the same command to resume (finished runs are skipped).

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

## 5. Test B1 students (queue 35, after queues 33 and 30)
The data is already built and packed in the repo: `custom_io/data_b1/plan_b.tgz` (13 MB; sha256
3c4042a64f39550f0bfa6fae9ffd5eae02779529d1e78c44477562b7c1ec2d20). Unpack it into the work dir so it gives `plan_b\teach` and `plan_b\gen`:
```
mkdir C:\Users\benja\custom-io\work\plan_b
tar -xzf custom_io\data_b1\plan_b.tgz -C C:\Users\benja\custom-io\work\plan_b
certutil -hashfile C:\Users\benja\custom-io\work\plan_b\teach\MANIFEST.json SHA256
certutil -hashfile C:\Users\benja\custom-io\work\plan_b\gen\MANIFEST.json SHA256
```
The two shas must equal the `- teach MANIFEST.json sha256` and `- gen MANIFEST.json sha256` lines in PASS-MARKS.md addendum 3
(40316ed1... and 9121d7ac...). If they differ, stop and say so. Re-stage `custom_io` from the branch first (the B1 code is newer than the copy
queue 33 froze). Then, once queues 33 and 30 have finished, the six runs (2 at a time, one device for all):
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\35-pc-b1-students.txt --device cuda --par 2 --busy C:\Users\benja\GPU-BUSY.txt
```
Push the results as in section 4 (no checkpoint.pt). Each run takes a few hours on the 5070 Ti.

## 6. The reader runs: EmbeddingGemma 2 as the reader, and B2 without its window (queue 36, BEFORE queue 35 since 10-06 4 PM ET)
**RETIRED 5:10 PM ET 10-06 (PASS-MARKS.md addendum 11): do not launch queue 36.** EGW, EGM and EGO all train on two rented 5090s
(custom_io/queue/egwA, egwB), each against plain B2 trained on the same box; the PC goes on to queues 35, 37 and 38. The text below is the record.
Marks: PASS-MARKS.md addenda 8 (EGM) and 7 (EGO). EGW (addendum 9) does not run here any more: at 0.75 updates/s and 16 GB it would hold the
card for about 18 h, so it runs on two rented 5090s with its own plain B2 there (addendum 10; custom_io/queue/egwA, egwB). They need the `eg_adapter` and `letters_in` switches (on the branch since
4:30 PM ET 10-06), so re-stage first. Since then the runner keeps one frozen code copy per queue AND code version
(WORK\code\QUEUE-HASH), so a relaunch after re-staging trains on the new code. Design: design/EG2-embedding.md. The runs need transformers >= 5.19, which the shared venv does not
have (it has 5.17, and the running queues use it), so it goes in its own folder. Queue 36 carries its own two variables in `# ENV`
lines (PYTHONPATH with that folder first, and CUSTOM_IO_EG2 = the local weights), and the runner hands them to every run of that queue
only, so a detached launch needs nothing set in the shell. Once, on the PC, in PowerShell (re-stage `custom_io` from the branch first;
queue 36 needs the newest code, the runner's `# ENV` support included):
```
python -m pip install --target C:\Users\benja\eg_site transformers==5.19.0
Remove-Item -Recurse -Force C:\Users\benja\eg_site\numpy, C:\Users\benja\eg_site\numpy-*.dist-info, C:\Users\benja\eg_site\numpy.libs -ErrorAction SilentlyContinue
$env:PYTHONPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
python -c "from huggingface_hub import snapshot_download; snapshot_download('google/embeddinggemma-2', revision='914f7f89142e33e77833254d9c9b90c3cef7303b', local_dir=r'C:\Users\benja\eg2')"
$env:CUSTOM_IO_EG2 = 'C:\Users\benja\eg2'
python -m custom_io.models.eg check cuda
```
The last line must print `"ok": true` (the text part is 271,002,624 params and 3 probe vectors match the build box's within cos 0.999;
bf16 on the build box's CPU gave 0.99988 or better). Removing eg_site's numpy keeps the venv's own, the one torch was installed with
(transformers 5.19 runs on Python 3.10 and only needs numpy >= 1.17). If the paths differ on the PC, edit the two `# ENV` lines of
`36-pc-eg2.txt` to match. Then launch it as soon as queue 30 is done, ahead of queue 35 (if queue 35 has already started, leave its
running runs alone and start 36 when the card has 7 GB free), detached like the others:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\36-pc-eg2.txt --device cuda --par 2 --busy C:\Users\benja\GPU-BUSY.txt
```
with stdout to `C:\Users\benja\custom-io\work\q36.log`; its first line must show `queue env: {...}` with both variables. Four runs
(EGM and EGO, seeds 200 and 201), paired with queue 33's B2_s200 and B2_s201 on this PC. EGR, R0, EGE and EGT are in queue 38 (section 8). Push the results as in section 4 (no
checkpoint.pt); the analysis is `python -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-egw-s200 custom_io/results/41-egw-s201 custom_io/results/42-eg-s200 custom_io/results/43-eg-s201`
(the last two come from the rented boxes; each arm is paired with plain B2 of the same machine).

## 7. Test LR, a readout loss at every round (queue 37, after queue 36, or alongside when the card has 6 GB free)
Marks: PASS-MARKS.md addendum 5. Plain B2 code plus one switch, no new packages (it does not need eg_site). From the same re-staged src:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\37-pc-loop-readout.txt --device cuda --par 2 --busy C:\Users\benja\GPU-BUSY.txt
```
Two runs (LR_s200, LR_s201), paired with queue 33's B2_s200 and B2_s201. Push as in section 4; the analysis is
`python -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/37-pc-loop-readout`.

## 8. EGR, R0, EGE and EGT (queue 38, after queue 37)
Marks: PASS-MARKS.md addenda 6 (EGR, R0) and 4 (EGE, EGT). Same EmbeddingGemma setup as section 6 (its `# ENV` lines are in the queue file):
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\38-pc-eg-teacher.txt --device cuda --par 2 --busy C:\Users\benja\GPU-BUSY.txt
```
Eight runs (EGR, R0, EGE and EGT, seeds 200 and 201). The analysis is `python -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/38-pc-eg-teacher`.
