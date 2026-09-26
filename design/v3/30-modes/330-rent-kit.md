# 330 rent kit: how month-end runs use a rented Linux GPU (month-end line, 2026-09-24)

Every `rent-33x-*` queue task says "follow design/v3/30-modes/330-rent-kit.md". Read all of it first.
Why rented: Ben, 12:29 UTC 2026-09-24: "remember you can also use cloud gpus". Also, BensPC runs Windows,
where the agent needed a Unix-only module (fixed for later with scripts/winshim/, but the rentals are Linux anyway).

## A. Getting your files (on the Mac)
Run `git fetch -q origin main builder-outbox`. Read files with `git show origin/main:<path>`. Never check out,
merge or push a branch yourself; the watcher pushes your PUSH paths. Build the code tree for the GPU:
```
# MAC DISK (09-26): never stage the full tree or a tree.tgz on the Mac (that took ~3 GB and filled it).
# Stream only the paths your task needs straight to the target, then delete nothing else:
git archive origin/builder-outbox <paths> | ssh <target> 'mkdir -p ~/tree && tar -x -C ~/tree'
git archive origin/main <paths> | ssh <target> 'tar -x -C ~/tree'          # main on top: main wins
scp <main checkout>/artifacts/fable-self122-20260922/self122_head.pt <target>:tree/artifacts/fable-self122-20260922/   # only if needed
```
For BensPC use its ssh host in place of <target>. If you truly must stage on the Mac, use one mktemp dir and
remove it by exact path before you finish. Put `DISK: <GB>` in the job header (peak Mac use; default 3 for rent-*).
self122_head.pt sha256 must be 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25.
- 0.2c STACK (Director 14:43 UTC 09-26, from mu-402): any rental that runs the 0.2c agent with route122 must also stream artifacts/fable-self127-20260922 (fable_self127.load_deltas reads deltas127.json every turn; missing it crashed mu-402's first A/B launch).
- TORCH UPGRADE (Director 15:25 UTC 09-26, from rd-378L WRITE-FAIL): if a job upgrades the image's torch (e.g. to 2.11), run `pip uninstall -y torchvision torchaudio` right after (the image's torchvision is built for torch 2.8 and breaks transformers/peft lazy imports), then an import check before any work.
- TORCH VERSION (Director 16:59 UTC 09-26, Thread manager report: torch 2.8 autocast cache can drop gradients on weights reused after no-grad steps; CPU repro, Sleep research confirming on a rental): every run report records `torch.__version__`. NEW jobs that TRAIN pin torch==2.11.0 (BensPC's version) with the TORCH UPGRADE step above, unless their seal says otherwise. Already-sealed jobs are not changed; eval-only jobs may keep 2.8.
- HELD JOBS (Director 17:10 UTC 09-26, after 358i2 launched from queue/ at 17:08): a job waiting on anything goes in handoff/held/, never handoff/queue/. The watcher also skips any queue file with a line starting "STATUS: HELD" (3c7022eca), but held/ is the rule.
- SPENDING RULE (Ben 18:54:40 UTC 09-26): no rental is released without Ben's own yes on a plan card (ELI5 plan artifact: what the money buys, goal + pass mark, this run's cap, expected spend until the problem is fixed, the free route). BensPC, CPU and GLM-on-opencode jobs need no plan.
If your task needs READER: the lis-301 merged reader is ~/premonition-models/lis301-merged/ on the Mac; its
model.safetensors sha256 must be b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890. Never push weights.

## B. Rental rules (the director's rent lane; Ben's limit: at most $4 per job, re-rents included)
- Search: `vastai search offers 'gpu_name=RTX_5090 reliability>=0.98 rentable=true' -o dph`, 4090 with the same
  filter if no 5090. At least 8 CPU cores, at least 60 GB disk, prefer upload/download >= 200 Mbps.
- Before renting: `vastai show instances`; if an instance with your task's label is live, exit with DUPLICATE.
  Label every instance with the task name. Never 2 instances for one task at once.
- Credit: check it and record it. No LOW-CREDIT stop (Ben, 18:21 UTC 2026-09-24: the vast.ai account auto-refills).
- LABELS (Director 13:33 UTC 2026-09-26): Ben's own agents share this vast account and one destroyed a rental it thought was its own. Every rental label starts with `claude-<thread>-<job>` (e.g. claude-fixsleep-dl4, claude-reading-lis319f). Never destroy an instance whose label your task did not create.
  The task's BUDGET, the $4 per-job cap and the $30 total cap still apply.
- Money: keep a running total of dph x hours for every instance you create. If it would pass your task's BUDGET,
  copy back what exists, destroy everything and stop with BUDGET-STOP.
- A new instance not "running" within 6 min (or create returns success False): destroy it by exact id, try another
  host; at most 4 rentals in total, then HOST-FAIL. A running job with no new log line for 10 min: watchdog,
  destroy and count it.
- Read the key only as $(cat ~/.config/vastai/vast_api_key); never print it.
- LESSON FROM rsn-296: copy every result file back to the Mac and check it arrived BEFORE destroying. Then destroy,
  confirm it is gone with `vastai show instances`, and append one line to artifacts/fable-predictions-ledger.md
  (cat >>): date, task, instance id(s), GPU, hours, dph, dollars, outcome.

## C. On the rental
```
(tree already streamed to ~/tree; scp READER only if needed); cd ~/tree
python -c "import torch;print(torch.__version__, torch.cuda.is_available())"   # image torch if True, else venv + CUDA torch
pip install -q "transformers>=5" safetensors huggingface_hub accelerate numpy
HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B')); print(s('sentence-transformers/all-MiniLM-L6-v2'))"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
python -c "import sys; sys.path.insert(0,'scripts'); import fable_self122 as S; print(S.route122('what is your name?'))"   # must not raise
```
BASE = the first printed snapshot path (Ben's yes 2026-09-23 covers this model; record its commit hash, expected
87179e5c1f455ef22e6223592d2d61351b525bfc). Run every step under nohup/setsid with a log file so an ssh drop
cannot kill it. Never download any other model.

## D. Independence
TEST-ONLY panels are never opened, printed or quoted; the runners read them. Never open judge_*.jsonl or
grammar_*.jsonl. The month-end thread wrote all code: run it, never edit it. If something breaks, copy back what
exists, destroy, and report the exact error and traceback.
