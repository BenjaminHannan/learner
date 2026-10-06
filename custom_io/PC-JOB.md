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

## 6. EmbeddingGemma 2 arms (queue 36, after queue 35, or alongside when the card has 7 GB free)
Marks: PASS-MARKS.md addendum 4. Design: design/EG2-embedding.md. The runs need transformers >= 5.19, which the shared venv does not
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
`36-pc-eg2.txt` to match. Then, once queue 35 has finished or while the card has 7 GB free, launch it detached like the others:
```
python -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\36-pc-eg2.txt --device cuda --par 2 --busy C:\Users\benja\GPU-BUSY.txt
```
with stdout to `C:\Users\benja\custom-io\work\q36.log`; its first line must show `queue env: {...}` with both variables. Four runs
(EGE and EGT, seeds 200 and 201), paired with queue 33's B2_s200 and B2_s201 on this PC. Push the results as in section 4 (no
checkpoint.pt); the analysis is `python -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/36-pc-eg2`.
