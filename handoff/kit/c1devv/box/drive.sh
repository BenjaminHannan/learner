#!/bin/bash
# c1-dev on ONE vast rental (Everyday chat thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# Same design as handoff/kit/sleep358sv/box/drive.sh; the arm commands are handoff/kit/c1devpc/remote/chain.cmd's, run on
# Linux. Pins torch 2.11.0+cu128 (BensPC's version) and transformers 5.17.0 (every earlier vast chat run), fail-closed; drops
# the image's torchvision/torchaudio (330 kit TORCH UPGRADE); downloads the three pinned model snapshots bm-390 used (the
# only downloads); checks SEAL-2 (24/24) and the four selftests; then runs the arms D, T, Q, L one after another into
# outC1/chat_<arm>.jsonl, each retried once if it exits non-zero (the runner skips conversations already written).
# Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>. It never edits code, never deletes anything,
# trains nothing and writes no weights. It runs once: a second start on the same disk refuses.
set -u
cd "${RC1V:-/root/r}" || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-c1dev-20260927
ARMS="D T Q L"
WINNL="winnl2: not Windows, nothing changed"          # claude_winnl2_wrap.py's line off Windows (BensPC printed the Windows one)
[ -e W/drive-state.txt ] && { echo "REFUSED: W/drive-state.txt exists (drive.sh already ran on this disk)"; exit 1; }
mkdir -p W outC1
echo $$ > W/drive.pid
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
GL=""
fail() { st "FAILED $*"; [ -n "$GL" ] && kill "$GL" 2>/dev/null; exit 1; }
# the real rental commands; the *C1V variables only point a mock run at stand-ins
PY=${PYC1V:-python}
pipi() { if [ -n "${PIPC1V:-}" ]; then $PIPC1V "$@"; else pip "$@"; fi; }
nvs() { if [ -n "${NVC1V:-}" ]; then $NVC1V "$@"; else nvidia-smi "$@"; fi; }
st START
st "HOST nproc $(nproc) disk $(df -h . | tail -1 | awk '{print $4}') free; $(nvs --query-gpu=name,memory.total,driver_version,compute_cap --format=csv,noheader 2>&1 | head -1)"
# one nvidia-smi line a minute (UTC time, MiB used, MiB total, watts, GPU %) for the whole run
( while :; do echo "$(date -u +%FT%TZ) $(nvs --query-gpu=memory.used,memory.total,power.draw,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ' | tr ',' ' ')" >> W/gpu_log.txt; sleep ${GLC1V:-60}; done ) &
GL=$!
# 1. torch 2.11.0+cu128, then transformers 5.17.0 and the kit C helpers
pipi install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
pipi uninstall -y torchvision torchaudio >> W/pip.log 2>&1
pipi install --no-cache-dir transformers==5.17.0 safetensors huggingface_hub accelerate numpy >> W/pip.log 2>&1 || fail "pip install transformers==5.17.0 (see W/pip.log)"
$PY -c "import torch, transformers, sys; x = torch.ones(4, device='cuda', dtype=torch.bfloat16).sum().item(); print('VERSIONS', torch.__version__, torch.version.cuda, transformers.__version__, sys.version.split()[0]); print('GPUNAME', torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0), 'bf16-sum', x)" > W/torch.txt 2>&1
grep -q '^VERSIONS 2\.11\.0' W/torch.txt && grep -q '^VERSIONS .* 5\.17\.0 ' W/torch.txt && grep -q ' bf16-sum 4\.0$' W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-240)"
st "TORCH $(tr '\n' ' ' < W/torch.txt)"
# 2. the three pinned snapshots (bm-390's; kit C); the only downloads. Tried twice.
dl() { HF_HUB_OFFLINE=0 $PY -c "from huggingface_hub import snapshot_download as s
print(s('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc'))
print(s('Qwen/Qwen3.5-2B', revision='15852e8c16360a2fea060d615a32b45270f8a8fc'))
print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'))"; }
dl > W/models.txt 2> W/dl.log || { st "DOWNLOAD retry"; dl > W/models.txt 2>> W/dl.log; } || fail "model download (see W/dl.log)"
BASE=$(sed -n 1p W/models.txt); Q2DIR=$(sed -n 2p W/models.txt); L12DIR=$(sed -n 3p W/models.txt)
case "$BASE" in */models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc) ;; *) fail "BASE path $BASE";; esac
case "$Q2DIR" in */models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc) ;; *) fail "Q2DIR path $Q2DIR";; esac
case "$L12DIR" in */models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b) ;; *) fail "L12DIR path $L12DIR";; esac
st "MODELS $(du -sh "$BASE/" "$Q2DIR/" "$L12DIR/" 2>/dev/null | awk '{printf "%s ", $1}')(pinned revisions)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
# 3. the seal and the four selftests (each through the winnl2 wrapper, as on BensPC)
n=$(sha256sum -c $A/SEAL-2.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 24 ] || fail "SEAL-2 $n/24"
st "SEAL-2 24/24"
chk() {
  local name=$1 want=$2 out rc first last; shift 2
  out=$($PY -B scripts/claude_winnl2_wrap.py "$@" 2>&1); rc=$?
  first=$(echo "$out" | head -1); last=$(echo "$out" | grep . | tail -1)
  echo "CHECK $name ok=$([ "$first" = "$WINNL" ] && [ "$last" = "$want" ] && echo 1 || echo 0) rc=$rc $(echo "$last" | cut -c1-160)"
}
{
  chk talker "c1dev talker selftest: 6/6 OK" scripts/claude_c1dev_talker.py --selftest
  chk ch403 "ch-403 run selftest: 6/6 OK" scripts/claude_ch403_run.py selftest
  chk c1rival "c1rival selftest: 5/5 OK" scripts/claude_c1rival_run.py selftest
  chk noise "c1dev noise selftest: 5/5 OK" scripts/claude_c1dev_noise.py --selftest
  grep '^VERSIONS\|^GPUNAME' W/torch.txt
} > W/checks.txt
[ "$(grep -c '^CHECK .* ok=1 ' W/checks.txt)" = 4 ] || fail "selftests $(grep -c '^CHECK .* ok=1 ' W/checks.txt)/4 (see W/checks.txt)"
st CHECKS-OK
# 4. the arms, one after another (chain.cmd's commands and order)
RUN="$PY -B scripts/claude_winnl2_wrap.py scripts/claude_twinb_wrap.py scripts/claude_ch403_run.py run --panel-dir artifacts/claude-chatdev-20260926 --out outC1"
arm() {
  local x=$1 kind=$2 m=$3 rc
  st "ARM $x start"; echo "$x start $(date -u +%FT%TZ)" >> W/steps.txt
  $RUN --arm "$kind" --name "$x" --gen-model "$m" > W/log$x.txt 2>&1; rc=$?
  echo "$x rc=$rc end $(date -u +%FT%TZ)" >> W/steps.txt
  if [ "$rc" != 0 ]; then
    echo "$x-retry start $(date -u +%FT%TZ)" >> W/steps.txt
    $RUN --arm "$kind" --name "$x" --gen-model "$m" > W/log$x-retry.txt 2>&1; rc=$?
    echo "$x-retry rc=$rc end $(date -u +%FT%TZ)" >> W/steps.txt
  fi
  st "ARM $x end rc $rc rows $([ -f outC1/chat_$x.jsonl ] && awk 'NF{n++} END{print n+0}' outC1/chat_$x.jsonl || echo 0)"
}
arm D claude_c1dev_talker:build_talker02d "$BASE"
arm T twin "$BASE"
arm Q twin "$Q2DIR"
arm L twin "$L12DIR"
kill "$GL" 2>/dev/null; GL=""
st DONE
