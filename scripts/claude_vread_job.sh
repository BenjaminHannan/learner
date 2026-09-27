# vread rental job (vector-reader thread, 2026-09-27). Passed to the vast instance as the container command:
#   args = ["bash", "-c", <this file>, "vread", <base64 chunk 1>, <base64 chunk 2>, ...]
# The chunks join to pack.tar.xz (the sealed scripts + artifacts/claude-vread-20260927/data), whose sha256 is put in
# PACK_SHA below by claude_vread_rent.py before the upload. Results leave through the container log (base64 between
# RESULTS-BEGIN / RESULTS-END, with its sha256). No credential is put on the machine. DRYRUN=1 stops after the checks.
set -u
PACK_SHA=__PACK_SHA__
BASE_REV=87179e5c1f455ef22e6223592d2d61351b525bfc
say() { echo "=== $* $(date -u +%FT%TZ)"; }
fail() { say "VREAD-FAIL $*"; results; say "VREAD DONE (failed)"; sleep 7200; exit 1; }
results() {
  cd "$J" 2>/dev/null || return
  ls out/*.jsonl out/*.log out/*.rc out/*.json out/vec/*.json out/vec/*.jsonl out/vec/final/*.json out/vec/final/*.jsonl \
     out/lora/summary.json out/lora/train_log.jsonl checks/* 2>/dev/null > files.txt
  tar -czf results.tar.gz -T files.txt 2>/dev/null
  say "RESULTS-BEGIN $(sha256sum results.tar.gz | cut -d' ' -f1) $(wc -c < results.tar.gz) bytes, $(wc -l < files.txt) files"
  base64 -w 4000 results.tar.gz
  say "RESULTS-END"
}
say "VREAD START"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1
echo "cpus $(nproc)"; free -g | head -2; df -h / | tail -1
J=${JOBDIR:-/job}
mkdir -p "$J/checks" "$J/out" && cd "$J" || exit 1
printf '%s' "$@" | base64 -d > pack.tar.xz
echo "$PACK_SHA  pack.tar.xz" | sha256sum -c || fail "pack sha256"
python -c "import tarfile; tarfile.open('pack.tar.xz', 'r:xz').extractall('.')" || fail "pack untar"   # the image has no xz binary
sha256sum -c SEAL-pack.sha256.txt > checks/pack_files.txt 2>&1 || { cat checks/pack_files.txt; fail "file sha256"; }
echo "pack files ok: $(wc -l < checks/pack_files.txt)"
python -c "import torch,sys;print('python',sys.version.split()[0],'torch',torch.__version__,torch.version.cuda,torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')" 2>&1 | tee checks/torch.txt
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
[ "${used:-0}" -gt 2000 ] && fail "GPU busy: $used MiB in use before any run"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==5.17.0" "peft==0.21.0" accelerate safetensors huggingface_hub numpy > checks/pip.log 2>&1 \
  || { tail -5 checks/pip.log; fail "pip"; }
python -c "import transformers,peft,torch;print('transformers',transformers.__version__,'peft',peft.__version__,'torch',torch.__version__)" \
  2>&1 | tee checks/versions.txt
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error PYTHONUTF8=1 TOKENIZERS_PARALLELISM=false
BASE=$(python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='$BASE_REV'))" 2> checks/download.err) \
  || { tail -3 checks/download.err; fail "model download"; }
export HF_HUB_OFFLINE=1
echo "base $BASE"; (cd "$BASE" && sha256sum *.safetensors) | tee checks/base_sha.txt
say "UNPACK"
python -B scripts/claude_vread_data.py unpack --data artifacts/claude-vread-20260927/data --out rows --tokenizer "$BASE" \
  > checks/unpack.json 2>&1 || { tail -5 checks/unpack.json; fail "unpack"; }
cat checks/unpack.json
say "CHECKS"
python -B scripts/claude_vread_model.py gradcheck --base "$BASE" --rows rows/train.cards.jsonl --layer 12 --device cuda \
  > checks/gradcheck.json 2> checks/gradcheck.err || { tail -5 checks/gradcheck.err; fail "gradcheck"; }
tail -1 checks/gradcheck.json
python -B scripts/claude_vread_model.py ptrcheck --base "$BASE" --rows rows/train.cards.jsonl --n 50 > checks/ptrcheck.json \
  2> checks/ptrcheck.err || { tail -5 checks/ptrcheck.err; fail "ptrcheck"; }
tail -1 checks/ptrcheck.json
[ "${DRYRUN:-0}" = 1 ] && { say "DRYRUN stop"; results; exit 0; }
mkdir -p lora-data && cat rows/train.jsonl rows/cal.jsonl > lora-data/train.jsonl && : > lora-data/dev.jsonl
echo "lora train rows $(wc -l < lora-data/train.jsonl)"
(while true; do sleep 300; echo "=== TICK $(date -u +%H:%M:%S) gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader) | lora $(tail -c 160 out/lora_train.log 2>/dev/null | tr '\n' ' ' | tail -c 120) | vec $(tail -qn1 out/vec_layers.log out/vec_train.log 2>/dev/null | tail -1 | tail -c 120)"; done) &
TICK=$!
say "PHASE A: LoRA training alongside the vector reader's layer pick, training and calibration read"
(timeout 150m python -B scripts/claude_lis300_train.py --model "$BASE" --data lora-data --out out/lora --epochs 2 --lr 2e-4 \
   --rank 32 --batch 16 --max-len 512 --seed 300 --merge > out/lora_train.log 2>&1; echo "lora_train rc=$?" > out/lora_train.rc) &
LP=$!
timeout 90m python -B scripts/claude_vread_model.py layers --base "$BASE" --train rows/train.cards.jsonl \
  --cal rows/cal.cards.jsonl --out out/vec > out/vec_layers.log 2>&1; echo "vec_layers rc=$?" | tee out/vec_layers.rc
L=$(python -c "import json;print(json.load(open('out/vec/layers.json'))['chosen'])" 2>/dev/null) || fail "no layer chosen"
say "vector layer chosen: $L"; cat out/vec/layers.json
timeout 120m python -B scripts/claude_vread_model.py train --base "$BASE" --train rows/train.cards.jsonl --layer "$L" \
  --out out/vec/final > out/vec_train.log 2>&1; echo "vec_train rc=$?" | tee out/vec_train.rc
timeout 60m python -B scripts/claude_vread_model.py read --base "$BASE" --ckpt out/vec/final/final.pt --rows rows/cal.cards.jsonl \
  --out out/vec_cal_reads.jsonl > out/vec_cal_read.log 2>&1; echo "vec_cal_read rc=$?" | tee out/vec_cal_read.rc
tail -2 out/vec_cal_read.log
say "waiting for LoRA training"
wait $LP; cat out/lora_train.rc; tail -c 1500 out/lora_train.log
say "PHASE B: each arm reads dev alone on the GPU"
timeout 120m python -B scripts/claude_lis319_read.py --model out/lora/merged --rows rows/dev.jsonl --out out/lora_dev_reads.jsonl \
  > out/lora_dev_read.log 2>&1; echo "lora_dev_read rc=$?" | tee out/lora_dev_read.rc
timeout 60m python -B scripts/claude_vread_model.py read --base "$BASE" --ckpt out/vec/final/final.pt --rows rows/dev.cards.jsonl \
  --out out/vec_dev_reads.jsonl > out/vec_dev_read.log 2>&1; echo "vec_dev_read rc=$?" | tee out/vec_dev_read.rc
tail -1 out/lora_dev_read.log out/vec_dev_read.log
kill $TICK 2>/dev/null
(sha256sum out/vec/final/final.pt out/lora/adapter/*.safetensors 2>/dev/null) | tee out/weights_sha.log
wc -l out/*reads.jsonl
results
say "VREAD DONE"
sleep 7200
