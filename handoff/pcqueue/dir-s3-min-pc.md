GPU: yes (BensPC RTX 5070 Ti; one job at a time; $0, NO rental, whatever fails). RUNNER: pc (runs on the BensPC runner, handoff/kit/pcwatch/watcher.sh; the runner writes and removes C:\Users\benja\GPU-BUSY.txt and holds this job while another job's name is in it, so it queues behind dir-g-a). Additive only, no secrets, download nothing, install nothing. TIME CAP: 600 minutes. LABEL: dir-s3-min-pc.
RUNNER: pc
Owner: helper S3 (thread "Numbers: nearest valid answer"), 2026-09-29. Marks sealed BEFORE this run: artifacts/claude-dir-s3-numbers-20260929/PASSMARKS.md. Code: scripts/claude_dir_s3_labels.py and scripts/claude_dir_s3_run.py (import dir-h2 and the sealed 358u code; never edit). One change vs dir-h2: the 4-number token loss is measured against the valid answer the net finds cheapest (min-loss). This job = the MIN arm: loop s13, plain s13, loop s14, plain s14 (two at once). The twin job dir-s3-random-pc is the RANDOM-VALID control. This job runs and copies back raw files only: no verdict, no gap (the blind recount does that).
STOP RULE: if a check or a run fails, print the first traceback verbatim, run nothing further, exit non-zero. Do not re-run with changed settings; do not patch scripts. Never open or print a test item: `eval` writes counts only, once per checkpoint.
EXIT CODES: 5 = WAITING (seal file not on main yet), 6 = SEAL-MISMATCH, 7 = NO-CUDA, 75 = network failure (the runner retries later).
PUSH: artifacts/claude-dir-s3-numbers-20260929/runs
```bash
set -u
MODE=min; TAG=s3min; PYB=/c/Users/benja/lis300/venv/Scripts/python.exe
W=/c/Users/benja/dir$TAG; KEEP=/c/Users/benja/premonition-models/dirs3/$MODE
export PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
date -u
[ -f "$TREE/artifacts/claude-dir-s3-numbers-20260929/SEAL-s3.sha256.txt" ] || { echo "WAITING: SEAL-s3 not on main"; exit 5; }
rm -rf "$W"; mkdir -p "$W" "$KEEP"
(cd "$TREE" && git archive HEAD scripts artifacts/claude-dir-s3-numbers-20260929 artifacts/claude-dir-h2-numbers-20260928 artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt artifacts/claude-rsn358i-20260926/tests) | tar -x -C "$W" || exit 75
cd "$W" || exit 1
sha256sum -c artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt || { echo SEAL-MISMATCH 358u; exit 6; }
sha256sum -c artifacts/claude-dir-s3-numbers-20260929/SEAL-s3.sha256.txt || { echo SEAL-MISMATCH s3; exit 6; }
sha256sum -c artifacts/claude-dir-h2-numbers-20260928/SEAL-h2.sha256.txt || { echo SEAL-MISMATCH h2; exit 6; }
$PYB -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" | tee cuda.txt; grep -q "True" cuda.txt || { echo NO-CUDA; exit 7; }
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
$PYB -B scripts/claude_rsn358a_envs.py selftest 2>&1 | tee ck1.txt; grep -q "selftest ok" ck1.txt || exit 1
$PYB -B scripts/claude_dir_h2_pool.py selftest 2>&1 | tee ck2.txt; grep -q "selftest ok" ck2.txt || exit 1
$PYB -B scripts/claude_rsn358u_run.py selftest 2>&1 | tee ck3.txt; grep -q "selftest ok" ck3.txt || exit 1
$PYB -B scripts/claude_dir_s3_labels.py selftest 2>&1 | tee ck4.txt; grep -q "s3 labels selftest ok" ck4.txt || exit 1
$PYB -B scripts/claude_dir_s3_run.py selftest 2>&1 | tee ck5.txt; grep -q "s3 run selftest ok" ck5.txt || exit 1
$PYB -B scripts/claude_dir_s3_run.py check-mask 2>&1 | tee ck6.txt; grep -q "check-mask ok" ck6.txt || exit 1
D="$TREE/artifacts/claude-dir-s3-numbers-20260929/runs/$MODE"; mkdir -p "$D"
for S in 13 14; do
  for ARM in loop plain; do
    $PYB -B scripts/claude_dir_s3_run.py train --mode $MODE --arm $ARM --seed $S --out "W/$ARM-s$S" > "$ARM-s$S.log" 2>&1 &
  done
  wait
  for ARM in loop plain; do
    grep -m1 "h2 pool:" "$ARM-s$S.log"
    [ -f "W/$ARM-s$S/final.pt" ] || { echo "TRAIN-FAILED $ARM-s$S"; tail -30 "$ARM-s$S.log"; exit 1; }
  done
done
for R in loop-s13 plain-s13 loop-s14 plain-s14; do
  echo "$(sha256sum W/$R/final.pt | cut -d' ' -f1)  $MODE/$R/final.pt" >> "$D/SEAL-run.sha256.txt"
  $PYB -B scripts/claude_dir_s3_run.py poison --ckpt W/$R/final.pt --out W/$R/poison.json > "$R.poison.txt" 2>&1 || { tail -30 "$R.poison.txt"; exit 1; }
  $PYB -B scripts/claude_dir_s3_run.py eval --ckpt W/$R/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$R/tests.json > "$R.eval.txt" 2>&1 || { tail -30 "$R.eval.txt"; exit 1; }
  $PYB -B scripts/claude_dir_s3_run.py extra --mode $MODE --ckpt W/$R/final.pt --out W/$R/extra.json > "$R.extra.txt" 2>&1 || { tail -30 "$R.extra.txt"; exit 1; }
  mkdir -p "$D/$R"
  cp W/$R/train_log.jsonl W/$R/train_summary.json W/$R/poison.json W/$R/tests.json W/$R/extra.json "$D/$R/" || exit 1
  cp "$R.log" "$D/$R/$R.log"; cp "$R.eval.txt" "$R.extra.txt" "$D/$R/"
  mkdir -p "$KEEP/$R"; cp W/$R/final.pt "$KEEP/$R/"
  grep "^numbers4" "$R.eval.txt" | cut -c1-120
done
cp cuda.txt ck5.txt "$D/"
date -u
```
