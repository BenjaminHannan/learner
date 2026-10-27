GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, NO rental, whatever fails). RUNNER: pc (runs on the BensPC runner, handoff/kit/pcwatch/watcher.sh; the runner writes and removes C:\Users\benja\GPU-BUSY.txt). Additive only, no secrets, download nothing, install nothing. TIME CAP: 90 minutes. LABEL: dir-lead0-retell-pc.
RUNNER: pc
Owner: copy of dir-lead0-retell-benspc.md for the PC runner (Director helper "PC runner", 2026-09-28). The original is untouched. Read-only check, no training. Pass marks sealed before the run: artifacts/claude-dir-lead0-20260928/PASSMARKS.md (PASS = 95 of 100 or more exact on BOTH grid seeds). It runs ON BensPC, so the scripts come from the runner's clone of main ($TREE).
DIFFERENCE FROM THE ORIGINAL: this job only runs and copies back the raw results (no RESULTS.md, that is a judgement step). The Director writes RESULTS.md from the pushed files and PASSMARKS.md.
EXIT CODES: 8 = MODEL-MISSING (download nothing), 75 = network failure (runner retries later).
PUSH: artifacts/claude-dir-lead0-20260928/run
```bash
set -u
PYB=/c/Users/benja/lis300/venv/Scripts/python.exe
L12DIR=C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
export PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
date -u
[ -d "$L12DIR" ] || { echo "MODEL-MISSING $L12DIR"; exit 8; }
cd "$TREE" || exit 1
$PYB -B scripts/claude_dir_lead0_retell.py selftest | tee "$JOBDIR/selftest.txt"; grep -q "lead0 selftest 3/3 ok" "$JOBDIR/selftest.txt" || exit 1
run() { $PYB -B scripts/claude_dir_lead0_retell.py run --model "$L12DIR" --out "$JOBDIR/run_lead0" --seeds 1,2 --n 100 > "$JOBDIR/log.txt" 2>&1; }
run || { if grep -qi "out of memory" "$JOBDIR/log.txt"; then run || { tail -30 "$JOBDIR/log.txt"; exit 1; }; else tail -30 "$JOBDIR/log.txt"; exit 1; fi; }
grep "lead0 seed" "$JOBDIR/log.txt"
D="$TREE/artifacts/claude-dir-lead0-20260928/run"; mkdir -p "$D"
cp "$JOBDIR"/run_lead0/* "$D/" && cp "$JOBDIR/log.txt" "$D/" || exit 1
$PYB -c "import torch;print(torch.__version__, torch.cuda.get_device_name(0))" > "$D/env.txt" 2>&1
```
