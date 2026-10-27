GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, NO rental, whatever fails). RUNNER: pc (runs on the BensPC runner, handoff/kit/pcwatch/watcher.sh; the runner writes and removes C:\Users\benja\GPU-BUSY.txt and holds this job while another job's name is in it). Additive only, no secrets, download nothing, install nothing. TIME CAP: 150 minutes. LABEL: dst-t3-1-s13-pc.
RUNNER: pc
Owner: copy of dst-t3-1-s13-benspc.md for the PC runner (Director helper "PC runner", 2026-09-28). The original is untouched. Same science: one seed of T3 (newer-weighted rehearsal across three nights), marks sealed in artifacts/claude-dir-t3-recency-20260928/PASSMARKS.md, code scripts/claude_dir_t3_recency.py (imports the sealed slp-358n3 night code; never edit either). Only the plumbing changed: it runs ON BensPC (no ssh, no Mac), so the tree comes from the runner's own clone of main ($TREE) and it is self-contained (no dependence on another T3 job having run first).
STOP RULE: if smoke or the run fails, print the first traceback verbatim, run nothing further, exit non-zero. Do not re-run with changed settings; do not fix the script.
EXIT CODES: 5 = WAITING (a checkpoint or sealed file is not there yet; the runner retries later), 6 = SEAL-MISMATCH, 7 = NO-CUDA, 75 = network failure (runner retries later).
CHECKPOINT NOTE: weights are never in git. ck/s13/final.pt must already be on BensPC at C:/Users/benja/dirt3/ck/s13/final.pt (the Mac job copied it there). If it is missing this job exits 5 and says so; it cannot fetch it from the Mac.
PUSH: artifacts/claude-dir-t3-recency-20260928/runs
```bash
set -u
S=13; T3DIR=/c/Users/benja/dirt3; PYB=/c/Users/benja/lis300/venv/Scripts/python.exe
export PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
date -u
[ -f "$TREE/artifacts/claude-dir-t3-recency-20260928/SEAL-code.sha256.txt" ] || { echo "WAITING: seal file not on main"; exit 5; }
mkdir -p "$T3DIR"
if [ ! -f "$T3DIR/ck/s$S/final.pt" ]; then echo "MISSING-CKPT: $T3DIR/ck/s$S/final.pt (copy it from the Mac once)"; exit 5; fi
(cd "$TREE" && git archive HEAD scripts artifacts/claude-slp358n3-20260927 artifacts/claude-rsn358i-20260926/tests artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt artifacts/claude-dir-t3-recency-20260928) | tar -x -C "$T3DIR" || exit 75
cd "$T3DIR" || exit 1
want=$(grep " loop-s$S/final.pt$" artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt | cut -d' ' -f1); have=$(sha256sum ck/s$S/final.pt | cut -d' ' -f1)
[ -n "$want" ] && [ "$want" = "$have" ] || { echo "SEAL-MISMATCH checkpoint s$S"; exit 6; }
sha256sum -c artifacts/claude-dir-t3-recency-20260928/SEAL-code.sha256.txt || { echo SEAL-MISMATCH; exit 6; }
sha256sum -c artifacts/claude-slp358n3-20260927/SEAL-code.sha256.txt || { echo SEAL-MISMATCH; exit 6; }
$PYB -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))" | tee cuda.txt; grep -q "True" cuda.txt || { echo NO-CUDA; exit 7; }
$PYB -B scripts/claude_rsn358u_run.py selftest || exit 1
$PYB -B scripts/claude_dir_t3_recency.py smoke | tee smoke.txt; grep -q "smoke ok" smoke.txt || exit 1
cp artifacts/claude-slp358n3-20260927/run-vast/sizes.json sizes.json
run() { $PYB -B scripts/claude_dir_t3_recency.py run --ckpt ck/s$S/final.pt --seed $S --sizes sizes.json --out run_s$S > log_s$S.txt 2>&1; }
run || { if grep -qi "out of memory" log_s$S.txt; then run || { tail -30 log_s$S.txt; exit 1; }; else tail -30 log_s$S.txt; exit 1; fi; }
grep -c morning log_s$S.txt
D="$TREE/artifacts/claude-dir-t3-recency-20260928/runs/s$S"; mkdir -p "$D"
cp run_s$S/dirt3-seed$S.json "$D/" && cp log_s$S.txt "$D/" || exit 1
$PYB -c "import json;d=json.load(open('run_s$S/dirt3-seed$S.json'));print({k:d.get(k) for k in ('minutes','torch','gpu')});print([v for k,v in d.items() if 'INTEGRITY' in k.upper() or 'integrity' in k])"
```
