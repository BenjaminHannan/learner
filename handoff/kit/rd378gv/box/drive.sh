#!/bin/bash
# rd-378g on ONE vast rental (Trustworthy notes thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# The same steps, commands and settings as the BensPC chain (handoff/kit/rd378gpc/remote/chain.cmd, ADDENDUM-L), in bash:
#   setup   check the card (GPU RAM in MB, from nvidia-smi), pin torch 2.11.0+cu128 (fail-closed) with transformers 5.17.0 and
#           peft 0.21.0 (rd-378u's rental versions, which rebuilt the rd-378 writer bit for bit), download the base
#           (openbmb/MiniCPM5-1B at 87179e5c) and MiniLM (1110a243) once, fetch locomo10.json and check its sha256,
#           check the seals and the four selftests
#   chain   dialogs, train, devcheck, write59 (each stops the chain on a failure), score, whenoff, g5G, then g5R once R
#           has reached the rental (rsend.sh from the Mac; at most RWAIT minutes, then g5R is skipped: ADDENDUM-K's 57% fallback)
#   seal    sha256 of G's adapter, merged model and every output into W/SEAL-run.sha256.txt
# Progress lines go to W/drive-state.txt (the last is DONE or FAILED <why>); step lines to W/steps.txt, as on BensPC.
# LoCoMo files (the raw file, dialogs59, g59, per_question) stay in DATA/ and P/, never in W/. It never edits code and never
# deletes anything.
set -u
cd "${RROOT:-/root/r}" || exit 1
export PATH=/opt/conda/bin:$PATH
N=artifacts/claude-rd378g-20260926
K=handoff/kit/rd378gpc/remote/check378g.py
MINRAM_MB=${1:-16000}; RWAIT=${2:-60}
LOCOMO_URL=https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json
LSHA=${LSHA378V:-79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4}
R_SHA=${RSHA378V:-dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510}
MINILM=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
mkdir -p W P DATA
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
sl() { echo "$* $(date -u +%FT%TZ)" >> W/steps.txt; }
okc() { sha256sum -c "$1" 2>/dev/null | grep -c ': OK$'; }
st START
[ -e W/steps.txt ] && fail "W/steps.txt already exists (never a second chain)"
GL=$(nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader,nounits 2>&1 | head -1)
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; GPU $GL"
mt=$(echo "$GL" | awk -F', ' '{print int($2)}')
# nvidia-smi gives MiB; a 16 GB card shows about 16300 MiB, so the floor here is 95% of the MB floor
[ "${mt:-0}" -ge $(( MINRAM_MB * 95 / 100 )) ] || fail "GPU RAM ${mt:-?} MiB is under $(( MINRAM_MB * 95 / 100 )) MiB"
ok=0; for t in 1 2; do pip install --no-cache-dir -q torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 >> W/pip.log 2>&1 && { ok=1; break; }; done
[ $ok = 1 ] || fail "pip install torch==2.11.0 (see W/pip.log)"
pip uninstall -y torchvision torchaudio >> W/pip.log 2>&1
pip install --no-cache-dir -q transformers==5.17.0 peft==0.21.0 safetensors huggingface_hub accelerate numpy >> W/pip.log 2>&1 || fail "pip install transformers/peft (see W/pip.log)"
python -c "import importlib.util as u, torch, transformers, peft; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), 'transformers', transformers.__version__, 'peft', peft.__version__, 'torchvision', u.find_spec('torchvision'))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt && grep -q 'transformers 5.17.0 peft 0.21.0 torchvision None' W/torch.txt || fail "import check: $(tr '\n' ' ' < W/torch.txt | cut -c1-240)"
st "TORCH $(cat W/torch.txt)"
unset HF_HOME HF_HUB_CACHE
HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc')); print(s('sentence-transformers/all-MiniLM-L6-v2', revision='$MINILM', allow_patterns=['*.json', 'model.safetensors', 'vocab.txt']))" > W/hf.txt 2> W/hf.err
BASE=$(sed -n 1p W/hf.txt); ML=$(sed -n 2p W/hf.txt)
[ -d "$BASE" ] || fail "base download (see W/hf.err)"
case "$ML" in */$MINILM) ;; *) fail "MINILM-PATH: '$ML'";; esac
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
m=$(python -c "import sys; sys.path.insert(0, 'scripts'); import fable_self122_train as T; print(T.resolve_snapshot(None))" 2>&1 | tail -1)
case "$m" in *"$MINILM") ;; *) fail "MINILM: resolve_snapshot gives '$(echo "$m" | cut -c1-160)'";; esac
st "BASE $BASE; MINILM ok"
{
  echo "BASESHA $(sha256sum "$BASE"/*.safetensors 2>/dev/null | awk '{print $1}' | tr '\n' ' ')(BensPC's lis300 base: 7ab8fd86563125929be78aeec8cb3969c7ed2ead3be1ab9d3ec0a9fa69c8660d; report only)"
  echo "SEALB $(okc $N/SEAL-B.sha256.txt) $(grep -c . $N/SEAL-B.sha256.txt)"
  echo "SEALK $(okc $N/SEAL-ADD-K.sha256.txt) $(grep -c . $N/SEAL-ADD-K.sha256.txt)"
  echo "SEALAB $(( $(okc $N/SEAL-ADD-A.sha256.txt) + $(okc $N/SEAL-ADD-B.sha256.txt) ))"
  echo "SEALN $(okc $N/SEAL-ADD-N.sha256.txt) $(grep -c . $N/SEAL-ADD-N.sha256.txt)"
  echo "SEAL0 $(okc $N/SEAL.sha256.txt) $(sha256sum -c $N/SEAL.sha256.txt 2>/dev/null | grep ': FAILED' | cut -d: -f1 | tr '\n' ' ')"
  for s in "claude_rd378u_confirm.py selftest|RD378U-SELFTEST PASS" "claude_ep382_store_v4.py selftest|EP382-V4-SELFTEST PASS" \
           "claude_rd378L_recall.py selftest|RD378L-SELFTEST PASS" "claude_rd378g_whenoff.py selftest|RD378G-WHENOFF-SELFTEST PASS"; do
    want=${s#*|}; s=${s%|*}
    out=$(python -B scripts/$s 2>&1); rc=$?
    echo "$out" | grep -q "$want" || { [ "$rc" = 0 ] && rc=97; }
    echo "CHECK ${s% *} rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
  done
} > W/checks.txt 2>&1
grep -q '^SEALB 8 8$' W/checks.txt || fail "SEAL-B (see W/checks.txt)"
grep -q '^SEALK 6 6$' W/checks.txt || fail "SEAL-ADD-K (see W/checks.txt)"
grep -q '^SEALAB 5$' W/checks.txt || fail "SEAL-ADD-A + B (see W/checks.txt)"
n=$(grep '^SEALN ' W/checks.txt | awk '{print $2}'); [ -n "$n" ] && [ "$n" -gt 0 ] && grep -q "^SEALN $n $n\$" W/checks.txt || fail "SEAL-ADD-N (see W/checks.txt)"
grep -q '^SEAL0 13 scripts/claude_lis300_train.py $' W/checks.txt || fail "SEAL.sha256.txt: needs 13 OK and only scripts/claude_lis300_train.py FAILED (ADDENDUM-A)"
[ "$(grep -c '^CHECK .* rc=0 ' W/checks.txt)" = 4 ] || fail "selftests (see W/checks.txt)"
st "SEALS and 4 selftests ok"
ok=0; for t in 1 2 3 4; do python -c "import urllib.request as u; u.urlretrieve('$LOCOMO_URL', 'DATA/locomo10.json')" 2>> W/fetch.err && ok=1 && break; sleep $((t * 4)); done
d=$(sha256sum DATA/locomo10.json 2>/dev/null | cut -c1-64)
[ $ok = 1 ] && [ "$d" = $LSHA ] || fail "DATA-MISMATCH: locomo10.json sha256 ${d:-missing}"
st "DATA ok"

# the chain (as chain.cmd)
sl dialogs start
python -B scripts/claude_rd378L_recall.py dialogs --data DATA --convs 5-9 --out P/dialogs59.jsonl > W/dialogs_log.txt 2>&1; RC=$?
[ $RC = 0 ] && { python -B $K dialogs-hash P/dialogs59.jsonl >> W/dialogs_log.txt 2>&1; RC=$?; }
sl dialogs rc=$RC end; [ $RC = 0 ] || { st "CHAIN-END dialogs rc=$RC"; st DONE; exit 0; }

sl train start
G=W/g; echo W/g > W/g-dir.txt
python -B scripts/claude_lis300_train.py --model "$BASE" --data $N/glm3U/rows --out W/g --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 512 --max-minutes 60 --seed 300 --merge > W/train_log.txt 2>&1; RC=$?
if [ $RC != 0 ] && grep -qi "out of memory" W/train_log.txt; then
  sl train rc=$RC oom, retry once with --batch 8 into W/g_b8
  G=W/g_b8; echo W/g_b8 > W/g-dir.txt
  python -B scripts/claude_lis300_train.py --model "$BASE" --data $N/glm3U/rows --out W/g_b8 --epochs 2 --lr 2e-4 --rank 32 --batch 8 --max-len 512 --max-minutes 60 --seed 300 --merge >> W/train_log.txt 2>&1; RC=$?
fi
sl train rc=$RC end; [ $RC = 0 ] || { st "CHAIN-END train rc=$RC"; st DONE; exit 0; }
# seal G's weights at once, so a copy after a later stop (money, time, stall) can still be checked and the rental destroyed
for f in $G/adapter/* $G/merged/model.safetensors; do [ -f "$f" ] && sha256sum "$f" >> W/SEAL-run.sha256.txt; done
st "PEAKMEM train $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1) MiB used now"

sl devcheck start
python -B scripts/claude_rd378_write.py --model $G/merged --dialogs $N/glm3U/rows/dev_dialogs.jsonl --out W/gdev.jsonl > W/devcheck_log.txt 2>&1; RC=$?
[ $RC = 0 ] && { python -B $K dev-check W/gdev.jsonl >> W/devcheck_log.txt 2>&1; RC=$?; }
sl devcheck rc=$RC end; [ $RC = 0 ] || { st "CHAIN-END devcheck rc=$RC"; st DONE; exit 0; }

sl write59 start
python -B scripts/claude_rd378_write.py --model $G/merged --dialogs P/dialogs59.jsonl --out P/g59.jsonl > W/write59_log.txt 2>&1; RC=$?
[ $RC = 0 ] && python -B $K count P/g59.jsonl >> W/write59_log.txt 2>&1
sl write59 rc=$RC end; [ $RC = 0 ] || { st "CHAIN-END write59 rc=$RC"; st DONE; exit 0; }

sl score start
python -B scripts/claude_rd378u_confirm.py score --data DATA --convs 5-9 --notes P/g59.jsonl --out P/outg > W/score_log.txt 2>&1; RC=$?
sl score rc=$RC end
sl whenoff start
python -B scripts/claude_rd378g_whenoff.py score --data DATA --convs 5-9 --notes P/g59.jsonl --out P/outg_whenoff > W/whenoff_log.txt 2>&1; RC=$?
sl whenoff rc=$RC end
sl g5G start
python -B scripts/claude_rd378_write.py --model $G/merged --dialogs $N/g5/dialogs.jsonl --out W/g5_G.jsonl > W/g5G_log.txt 2>&1; RC=$?
[ $RC = 0 ] && python -B $K count W/g5_G.jsonl >> W/g5G_log.txt 2>&1
sl g5G rc=$RC end

# R: rsend.sh on the Mac writes W/R-OK after the rental's sha256 of R matches, or W/R-FAIL; wait at most RWAIT minutes
RD=R/rd378-notes-merged; w=0
while [ ! -e W/R-OK ] && [ ! -e W/R-FAIL ] && [ $w -lt "$RWAIT" ]; do [ $((w % 5)) = 0 ] && st "WAIT-R $w min"; sleep 60; w=$((w+1)); done
if [ -e W/R-OK ] && [ "$(sha256sum $RD/model.safetensors 2>/dev/null | cut -c1-64)" = $R_SHA ]; then
  echo "$(pwd)/$RD" > W/r-path.txt
  sl g5R start
  python -B scripts/claude_rd378_write.py --model $RD --dialogs $N/g5/dialogs.jsonl --out W/g5_R.jsonl > W/g5R_log.txt 2>&1; RC=$?
  [ $RC = 0 ] && python -B $K count W/g5_R.jsonl >> W/g5R_log.txt 2>&1
  sl g5R rc=$RC end
else
  sl g5R skipped "$( [ -e W/R-FAIL ] && head -c 120 W/R-FAIL | tr '\n' ' ' || echo "R not on the rental after $RWAIT min")"
fi

# counts and positions only go to W (pushable); the LoCoMo-derived files stay in P
for f in outg/notes_confirm.json:notes_confirm.json outg/ranked_turns.jsonl:ranked_turns.jsonl outg_whenoff/notes_confirm.json:notes_confirm_whenoff.json; do
  [ -f "P/${f%%:*}" ] && cp "P/${f%%:*}" "W/${f#*:}"; done
for f in W/gdev.jsonl W/g5_G.jsonl W/g5_R.jsonl P/dialogs59.jsonl P/g59.jsonl; do
  [ -f "$f" ] && sha256sum "$f" >> W/SEAL-run.sha256.txt; done
st "SEALED $(grep -c . W/SEAL-run.sha256.txt 2>/dev/null) files"
st DONE
