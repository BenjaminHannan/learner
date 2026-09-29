GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, NO rental, whatever fails). RUNNER: pc (runs on the BensPC runner, handoff/kit/pcwatch/watcher.sh; the runner holds this job while C:\Users\benja\GPU-BUSY.txt names another job, so it waits behind dir-g-a). Additive only, no secrets, install nothing, no model download. TIME CAP: 120 minutes. LABEL: dir-s5-talker-notes-pc.
RUNNER: pc
Owner: Director helper dir-s5 (2026-09-29). Test 5 of the lead sweep: can the plain LFM2.5-1.2B talker read the right notes? Marks sealed BEFORE this job in artifacts/claude-dir-s5-lme-20260929/PASSMARKS.md (seal: SEAL-s5.sha256.txt). Code scripts/claude_dir_s5_run.py + claude_dir_s5_slice.py; never edit either.
DATA GUARD: only the 100 dev ids in dev100.ids.txt are used. The one network call is the dataset file (277 MB, a dataset, not a model), pinned by sha256; if HuggingFace is not reachable the job exits 75 and the runner retries. Benchmark text stays in $JOBDIR scratch (outside git); only counts and 0/1 flags are pushed.
STOP RULE: if the smoke or the run fails, print the first traceback verbatim, run nothing further, exit non-zero. Do not re-run with changed settings; do not fix the script.
EXIT CODES: 5 = WAITING (model missing), 6 = SEAL-MISMATCH, 7 = NO-CUDA, 75 = network failure (runner retries later).
PUSH: artifacts/claude-dir-s5-lme-20260929/runs
```bash
set -u
PYB=/c/Users/benja/lis300/venv/Scripts/python.exe
L12=/c/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
W=/c/Users/benja/dirs5; A=artifacts/claude-dir-s5-lme-20260929
export PYTHONUTF8=1 OMP_NUM_THREADS=4 HF_HUB_OFFLINE=1
date -u
[ -f "$TREE/$A/SEAL-s5.sha256.txt" ] || { echo "WAITING: seal file not on main"; exit 5; }
[ -d "$L12" ] || { echo "MODEL-MISSING $L12 (download nothing)"; exit 5; }
mkdir -p "$W" && rm -rf "$W/tree" && mkdir -p "$W/tree" || exit 1
(cd "$TREE" && git archive HEAD scripts $A) | tar -x -C "$W/tree" || exit 75
cd "$W/tree" || exit 1
sha256sum -c $A/SEAL-s5.sha256.txt || { echo SEAL-MISMATCH; exit 6; }
$PYB -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))" | tee cuda.txt; grep -q "True" cuda.txt || { echo NO-CUDA; exit 7; }
$PYB -B scripts/claude_dir_s5_run.py selftest || exit 1
if [ ! -f "$W/s.json" ]; then
  curl -fsSL -m 1800 -o "$W/s.part" "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json" || exit 75
  mv "$W/s.part" "$W/s.json"
fi
[ "$(sha256sum "$W/s.json" | cut -d' ' -f1)" = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442" ] || { rm -f "$W/s.json"; echo "DATA-SHA-MISMATCH"; exit 75; }
$PYB -B scripts/claude_dir_s5_slice.py check "$W/s.json" || exit 6
rm -rf "$W/smoke"; $PYB -B scripts/claude_dir_s5_run.py run --data "$W/s.json" --model "$L12" --work "$W/smoke/work" --out "$W/smoke/out" --limit 3 > smoke.txt 2>&1 || { tail -40 smoke.txt; exit 1; }
tail -5 smoke.txt
rm -rf "$W/run"; $PYB -B scripts/claude_dir_s5_run.py run --data "$W/s.json" --model "$L12" --work "$W/run/work" --out "$W/run/out" > log.txt 2>&1 || { tail -40 log.txt; exit 1; }
D="$TREE/$A/runs"; mkdir -p "$D"
cp "$W"/run/out/*.json "$W"/run/out/flags.jsonl "$D/" && cp log.txt "$D/" || exit 1
tail -60 log.txt
```
