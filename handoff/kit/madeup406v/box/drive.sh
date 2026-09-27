#!/bin/bash
# mu-406 on ONE vast rental ("Making things up about you" thread, Claude, 2026-09-27). Runs ON the rental, detached (setsid
# nohup), from /root/r. Same design as the sleep research thread's handoff/kit/sleep358sv/box/drive.sh. It runs PASSMARKS.md
# steps 6 and the GPU half of 7 with the sealed scripts, unchanged, in order:
#   1. torch 2.11.0+cu128 (BensPC's version), transformers 5.17.0 and peft 0.21.0 (the versions the scripts were tested with);
#      fail closed on any other version
#   2. the plain 1B, openbmb/MiniCPM5-1B at revision 87179e5c (the approved base, the same snapshot BensPC holds)
#   3. SEAL 30/30, SEAL-panel 4/4 (paths relative to the mu406 folder), SEAL-data (every line); the three selftests
#   4. bm-390's pinned public data for the no-harm check (GSM8K 300 and MMLU-Redux 300, sha256-checked by claude_bm390.py)
#   5. the LoRA on the sealed rows (k1h's fixed recipe), its adapter sealed in W/SEAL-run.sha256.txt, then the merged copy
#   6. the smoke run (3 chats, P and T; not judged)
#   7. the five arms (P, T, N, PW, TW) and the four no-harm runs (GSM8K and MMLU-Redux for P and T), all on this card, each
#      started only while 6 GB of GPU memory is free, then the no-harm score (claude_mu406_judge.py noharm)
# Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>. It never edits code and never deletes anything.
# W/ is copied back to the Mac; X/ (the merged copy and the benchmark files) never leaves the rental.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-mu406-20260926
MODEL_ID=openbmb/MiniCPM5-1B; REV=87179e5c1f455ef22e6223592d2d61351b525bfc
PN=$A/panel/items.jsonl; FR=artifacts/claude-mu407-20260927/prep/frames.json; ROWS=$A/train/rows.jsonl
mkdir -p W W/run W/gen W/smoke X
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
freemb() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
[ -e W/drive-state.txt ] && { echo "drive.sh already ran here"; exit 1; }
st START
st "HOST nproc $(nproc) ram $(free -g 2>/dev/null | awk '/Mem:/{print $2}') GB, disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
# 1. environment
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
pip uninstall -y torchvision torchaudio >> W/pip.log 2>&1
pip install --no-cache-dir transformers==5.17.0 peft==0.21.0 safetensors huggingface_hub accelerate numpy pyarrow >> W/pip.log 2>&1 || fail "pip install transformers/peft (see W/pip.log)"
python -c "import torch, transformers, peft; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), '| transformers', transformers.__version__, '| peft', peft.__version__)" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt && grep -q '| transformers 5.17.0 | peft 0.21.0' W/torch.txt || fail "version check: $(tr '\n' ' ' < W/torch.txt | cut -c1-240)"
st "TORCH $(cat W/torch.txt)"
# 2. the plain 1B at the pinned revision
BASE=$(python -c "from huggingface_hub import snapshot_download as s; print(s('$MODEL_ID', revision='$REV'))" 2> W/model.err | tail -1)
case "$BASE" in */$REV) ;; *) fail "model download: '$BASE' (see W/model.err)";; esac
[ -f "$BASE/config.json" ] || fail "model download: no config.json in $BASE"
echo "$BASE" > W/base.txt; st "MODEL $BASE"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
# 3. seals and selftests (fail closed)
n=$(sha256sum -c $A/SEAL.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 30 ] || fail "SEAL $n/30"
np=$( (cd $A && sha256sum -c SEAL-panel.sha256.txt 2>/dev/null) | grep -c ': OK$'); [ "$np" = 4 ] || fail "SEAL-panel $np/4"
nd=$(grep -c . $A/SEAL-data.sha256.txt); nk=$(sha256sum -c $A/SEAL-data.sha256.txt 2>/dev/null | grep -c ': OK$')
[ "$nd" -gt 0 ] && [ "$nk" = "$nd" ] || fail "SEAL-data $nk/$nd"
grep -q " $ROWS\$" $A/SEAL-data.sha256.txt || fail "SEAL-data does not list $ROWS"
st "SEALS SEAL $n/30, SEAL-panel $np/4, SEAL-data $nk/$nd"
{ python -B scripts/claude_mu406_train.py selftest; python -B scripts/claude_mu406_talk.py --selftest; python -B scripts/claude_mu406_judge.py selftest; } > W/checks.txt 2>&1
grep -q 'mu406 train selftest 8/8 ok' W/checks.txt && grep -q 'mu406 talk selftest 5/5 ok' W/checks.txt && grep -q 'mu406 judge selftest 17/17 ok' W/checks.txt || fail "selftests (see W/checks.txt)"
st CHECKS-OK
# 4. public benchmark files for the no-harm check
python -B scripts/claude_bm390.py fetch --data X/DATA > W/data.txt 2>&1 || fail "bm390 fetch rc (see W/data.txt)"
grep -q '"mmlu_sample": 300' W/data.txt && grep -q '"gsm8k_sample": 300' W/data.txt || fail "bm390 samples: $(tail -1 W/data.txt | cut -c1-200)"
st "DATA $(tail -1 W/data.txt | cut -c1-300)"
# 5. the LoRA and the merged copy
st "TRAIN-START rows $(grep -c . $ROWS)"
python -B scripts/claude_mu406_train.py train --model "$BASE" --rows $ROWS --out W/train > W/train.log 2>&1; rc=$?
[ $rc = 0 ] || fail "train rc $rc (see W/train.log)"
[ -s W/train/adapter/adapter_model.safetensors ] && [ -s W/train/summary.json ] || fail "train: no adapter or summary"
echo "$(sha256sum W/train/adapter/adapter_model.safetensors | cut -c1-64)  train/adapter/adapter_model.safetensors" > W/SEAL-run.sha256.txt
st "SEALED adapter $(cut -c1-16 W/SEAL-run.sha256.txt)"
python -B scripts/claude_mu406_train.py merge --model "$BASE" --adapter W/train/adapter --out X/merged > W/merge.log 2>&1; rc=$?
[ $rc = 0 ] && [ -s X/merged/mu406_merged.json ] || fail "merge rc $rc (see W/merge.log)"
cp X/merged/mu406_merged.json W/train/mu406_merged.json
st "MERGED $(tail -1 W/merge.log | cut -c1-200)"
# 6. smoke (not judged)
for arm in P T; do M=$BASE; [ $arm = T ] && M=X/merged
  python -B scripts/claude_mu406_talk.py --panel $PN --frames $FR --model $M --arm $arm --out W/smoke --smoke > W/smoke/log$arm.txt 2>&1 || fail "smoke $arm (see W/smoke/log$arm.txt)"
done
st "SMOKE-OK P $(tail -1 W/smoke/logP.txt | cut -c1-100) | T $(tail -1 W/smoke/logT.txt | cut -c1-100)"
# 7. the five arms and the no-harm runs (registered ones and the longest first)
JOBS="talk:P talk:T gen:gsm8k:P gen:gsm8k:T talk:N talk:PW talk:TW gen:mmlu:P gen:mmlu:T"
pids=""; names=""
for J in $JOBS; do
  w=0; while [ "$(freemb)" -lt 6144 ] 2>/dev/null; do [ $w = 0 ] && st "WAIT $J: $(freemb) MiB free"; w=1; sleep 30; done
  case $J in
    talk:*) arm=${J#talk:}; M=$BASE; case $arm in T|TW) M=X/merged;; esac
            python -B scripts/claude_mu406_talk.py --panel $PN --frames $FR --model $M --arm $arm --out W/run > W/run/log$arm.txt 2>&1 &;;
    gen:*)  t=$(echo $J | cut -d: -f2); arm=$(echo $J | cut -d: -f3); M=$BASE; [ $arm = T ] && M=X/merged
            python -B scripts/claude_bm390.py general --data X/DATA --task $t --arm plain:$M --name $arm --out W/gen > W/gen/log_${t}_$arm.txt 2>&1 &;;
  esac
  pids="$pids $!"; names="$names $J"; st "LAUNCH $J pid $! ($(freemb) MiB free before it loads)"; sleep 90
done
errs=""; set -- $names
for p in $pids; do wait $p; rc=$?; st "EXIT $1 rc $rc"; [ $rc = 0 ] || errs="$errs $1"; shift; done
st "PEAK-NOTE nvidia-smi now: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null | head -1)"
python -B scripts/claude_mu406_judge.py noharm --data X/DATA --gen W/gen > W/gen/noharm.log 2>&1; st "NOHARM rc $? $(tr -d '\n ' < W/gen/noharm.json 2>/dev/null | cut -c1-300)"
# per question right (1) or wrong (0), by qid, for P and T: lets the recount check the sums without the benchmark files
python - > W/gen/noharm_per.json 2> W/gen/noharm_per.err <<'EOS'
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import claude_bm390_score as SC, claude_mu402_judge as J402
out = {}
for task in ("mmlu", "gsm8k"):
    for arm in ("P", "T"):
        p = Path("W/gen") / f"{task}_{arm}.jsonl"
        if p.exists():
            out[f"{task}_{arm}"] = SC.score_general(Path("X/DATA"), task, J402.load(p))["per"]
print(json.dumps(out, sort_keys=True))
EOS
[ -n "$errs" ] && st "ERRORS:$errs (see their logs)"
st DONE
