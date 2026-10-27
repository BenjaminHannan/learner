BASH-ONLY: yes
GPU: no (Mac CPU, fp32, $0, no rental, download nothing, install nothing). LOAD-LIGHT: no (one process, 4 threads). TIME CAP: 300 minutes. LABEL: trn-decode-sums.
DISK: 1
Owner: helper "trn" (thread "Translator check"), 2026-09-29. Marks sealed BEFORE this run: artifacts/claude-dir-trn-20260929/PASSMARKS.md (files and hashes in SEAL-trn.sha256.txt). Read-only on the reasoner: frozen practised loop and plain nets, only a small decoder is trained. Dev panels only; the holdout and every blind panel are never opened. Additive only, no git by the job (the watcher pushes PUSH paths), no keys read.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero. Do not re-run with changed settings. Exit codes: 5 = WAITING/MISSING-NET, 6 = SEAL-MISMATCH.
SUMS-ONLY half (Director-approved via the channel session 2026-09-29 09:20 UTC; the mazes half stays in trn-decode-mac, HELD). NETS: $BM/artifacts/claude-fewex-20260927/runs/{loop,plain}-s{0,1}/source.pt. If any is missing print MISSING-NET and exit 5.
PUSH: artifacts/claude-dir-trn-20260929/run
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-trn-sums; A=artifacts/claude-dir-trn-20260929
BM=${TRN_BM:-/Users/ben-hannan/Desktop/projects/beautiful-model}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
echo "start $(date -u '+%F %T') UTC"; uptime
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" cat-file -e "origin/main:$A/SEAL-trn.sha256.txt" 2>/dev/null || { echo "WAITING: no seal on main"; exit 5; }
for S in 0 1; do for AR in loop plain; do
  for P in runs/$AR-s$S/source.pt; do [ -f "$BM/artifacts/claude-fewex-20260927/$P" ] || { echo "MISSING-NET: $P"; exit 5; }; done
done; done
rm -rf "$W"; mkdir -p "$W"
git -C "$G" archive origin/main scripts $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-trn.sha256.txt || { echo SEAL-MISMATCH; exit 6; }
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_dir_trn_decode.py selftest 2>&1 | tee $A/selftest.log
grep -q "trn selftest ok" $A/selftest.log || { echo "STOP: selftest failed"; exit 7; }
mkdir -p $A/run
for T in sums; do
  nohup $PY scripts/claude_dir_trn_decode.py run --src "$BM" --out $A/run --tasks $T --threads 4 > $A/run/log-$T.txt 2>&1 &
  echo "$T pid $!"
done
wait
for T in sums; do echo "== $T"; grep -c '^trn ' $A/run/log-$T.txt; tail -2 $A/run/log-$T.txt; done
[ -f $A/run/sums.json ] || { echo "RUN-FAILED"; exit 1; }
cp $A/selftest.log $A/run/selftest-sums.log
echo "done $(date -u '+%F %T') UTC"
```
