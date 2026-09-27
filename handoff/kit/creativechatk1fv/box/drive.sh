#!/bin/bash
# k1f on ONE vast rental (Creative answers in chat thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# The registered k1f run (PASSMARKS-k1f.md; machine per ADDENDUM-2-vast.md), eval only, no training. The steps and checks are
# rent-k1f's and k1f-benspc2's: the image's torch (eval-only rule, recorded), kit section C's pip line, the four models
# downloaded here at their pins, the seals, the five tests, the adapter and self122 checks, the route122 check, the DEV gate,
# the five arms each launched ONCE (all at once on >= 30000 MiB, else K F T first, then Q L), the V1 checks, the three
# scorers and the CRLF counts. Progress lines go to W/drive-state.txt (the last is DONE or FAILED <why>); count lines for
# the report go to W/report.txt; exact PIDs go to W/pids.txt. It never edits code, never deletes anything and never prints
# a reply, a draft or a test item (counts only).
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-k1f-20260926
P=artifacts/claude-k1fpanel-20260926/creative
D=artifacts/claude-k1a-dev-20260926
AD=/root/adapter/adapter02c.pt
TR=/root/r
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
rp() { echo "$*" >> W/report.txt; }
fin() { touch W/.end; st "$1"; exit "$2"; }
fail() { rp "FAILED $*"; fin "FAILED $*" 1; }
echo "drive $$" >> W/pids.txt
st START
rp "start $(date -u +%FT%TZ)"
rp "host: nproc $(nproc); disk free $(df -h /root | tail -1 | awk '{print $4}'); $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
TOTMB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
# peak GPU memory, sampled every 15 s until the end (one sampler; a sample, not profiling)
( m=0; while [ ! -e W/.end ]; do u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
    [ -n "$u" ] && [ "$u" -gt "$m" ] 2>/dev/null && { m=$u; echo "$m MiB of ${TOTMB:-?}" > W/gpumem-peak.txt; }; sleep 15; done ) &
echo "sampler $!" >> W/pids.txt

# 1. torch (the image's; eval only), then kit section C's pip line and an import check
python -c "import torch, sys; print('torch', torch.__version__, 'cuda', torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0)); print('python', sys.version.split()[0])" > W/torch.txt 2>&1
grep -q ' True ' W/torch.txt || fail "torch has no CUDA: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
T0V=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
pip install -q "transformers>=5" safetensors huggingface_hub accelerate numpy > W/pip.log 2>&1 || fail "pip (see W/pip.log)"
T1V=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
if [ "$T0V" != "$T1V" ]; then   # 330-rent-kit TORCH UPGRADE rule, only if pip moved torch
  rp "pip moved torch $T0V -> $T1V; TORCH UPGRADE rule: pip uninstall -y torchvision torchaudio"
  pip uninstall -y torchvision torchaudio >> W/pip.log 2>&1; fi
python -c "import torch, transformers, sys; from transformers import AutoModelForCausalLM, AutoTokenizer; print('torch', torch.__version__, 'transformers', transformers.__version__, 'python', sys.version.split()[0])" > W/versions.txt 2>&1 || fail "import check (see W/versions.txt)"
rp "versions: $(cat W/versions.txt)"
st "SETUP $(cat W/versions.txt)"

# 2. the four models at their pins (downloaded here only; one retry)
for t in 1 2; do
  HF_HUB_OFFLINE=0 HF_HUB_DISABLE_PROGRESS_BARS=1 python -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='87179e5c1f455ef22e6223592d2d61351b525bfc')); print(s('sentence-transformers/all-MiniLM-L6-v2')); print(s('Qwen/Qwen3.5-2B', revision='15852e8c16360a2fea060d615a32b45270f8a8fc')); print(s('LiquidAI/LFM2.5-1.2B-Instruct', revision='0f604ada3f766f9f257460c4c9f0b5d6f69d431b'))" > W/models.txt 2> W/download.err && break
  st "DOWNLOAD try $t failed"; sleep 30; done
[ "$(grep -c . W/models.txt 2>/dev/null)" = 4 ] || fail "model download (see W/download.err)"
BASE=$(sed -n 1p W/models.txt); MINI=$(sed -n 2p W/models.txt); Q2DIR=$(sed -n 3p W/models.txt); L12DIR=$(sed -n 4p W/models.txt)
[ "${BASE##*/}" = 87179e5c1f455ef22e6223592d2d61351b525bfc ] && [ "${Q2DIR##*/}" = 15852e8c16360a2fea060d615a32b45270f8a8fc ] && [ "${L12DIR##*/}" = 0f604ada3f766f9f257460c4c9f0b5d6f69d431b ] || fail "a model is not at its pinned commit (see W/models.txt)"
rp "BASE $BASE"; rp "MiniLM $MINI"; rp "Q2DIR $Q2DIR"; rp "L12DIR $L12DIR"
st MODELS-OK
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
unset SLEEP02C_ADAPTER K1F_WRITER_MODEL K1F_DRAFTS

# 3. seals, adapter, self122, route122
seal() { r=$(sha256sum -c "$2" 2>&1); n=$(echo "$r" | grep -c ': OK$'); b=$(echo "$r" | grep -vc ': OK$'); rp "seal $1: $n OK, $b other"
         [ "$n" = "$3" ] && [ "$b" = 0 ] || fail "SEAL-MISMATCH $1 ($n OK, $b other; want $3 OK)"; }
seal k1f $A/SEAL.sha256.txt 21
seal addendum1 $A/SEAL-addendum1.sha256.txt 2
seal addendum2 $A/SEAL-addendum2.sha256.txt 3
r=$(cd artifacts/claude-k1fpanel-20260926 && sha256sum -c SEAL.sha256.txt 2>&1); n=$(echo "$r" | grep -c ': OK$'); b=$(echo "$r" | grep -vc ': OK$')
rp "seal k1fpanel: $n OK, $b other"; [ "$n" = 1 ] && [ "$b" = 0 ] || fail "SEAL-MISMATCH k1fpanel"
r=$(sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt 2>&1); n=$(echo "$r" | grep -c ': OK$'); b=$(echo "$r" | grep -c ': FAILED')
rp "seal e2e02c SEAL-code (present files only): $n OK, $b FAILED"; [ "$n" -ge 1 ] && [ "$b" = 0 ] || fail "SEAL-MISMATCH e2e02c SEAL-code"
a=$(sha256sum "$AD" 2>/dev/null | cut -c1-64); rp "adapter $AD sha256 $a"
[ "$a" = a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 ] || fail "ADAPTER-MISMATCH"
[ -s /root/adapter/adapter02c.json ] || fail "adapter02c.json sidecar missing"
h=$(sha256sum artifacts/fable-self122-20260922/self122_head.pt 2>/dev/null | cut -c1-64); rp "self122_head.pt sha256 $h"
[ "$h" = 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 ] || fail "SELF122-MISMATCH"
python -c "import sys; sys.path.insert(0,'scripts'); import fable_self122 as S; print(S.route122('what is your name?'))" > W/route122.txt 2>&1 || fail "route122 check raised (see W/route122.txt)"
st SEALS-OK

# 4. the five tests (last line must match)
: > W/tests.txt
for t in "scripts/claude_k1a_test.py|k1a tests: 7/7 OK" "scripts/claude_k1f_test.py|k1f tests: 8/8 OK" "scripts/claude_k1f_score.py --selftest|k1f score selftest 6/6 ok" "scripts/claude_k1rival_score.py --selftest|k1rival score selftest 4/4 ok" "scripts/claude_mu402.py --selftest|mu402 selftest 7/7 ok"; do
  c=${t%%|*}; want=${t#*|}; echo "== $c" >> W/tests.txt
  python -B $c >> W/tests.txt 2>&1; got=$(tail -1 W/tests.txt); rp "test $c: $got"
  [ "$got" = "$want" ] || fail "TEST-FAIL $c (last line: $got)"; done
st TESTS-OK

# 5. DEV gate (readable DEV data, 40 chats), F env
mkdir -p devk1f
env K1F_WRITER_MODEL="$L12DIR" K1F_DRAFTS=$TR/devk1f/drafts_F.jsonl SLEEP02C_ADAPTER="$AD" python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $D --arm claude_k1f_cre:build_null_k1f --name F --model NULL --gen-model "$BASE" --out devk1f > W/logdevF.txt 2>&1 &
echo "dev $!" >> W/pids.txt; wait $!
rc=$?; n=$(grep -c '^\[382/creative/F\] ' W/logdevF.txt)
ad=$(grep -c "mu402: adapter loaded = $AD" W/logdevF.txt); wr=$(grep '^k1f: creative writer = install_creative_k1f; writer = lfm' W/logdevF.txt | grep -c '@0f604ada')
fb=$(python - <<'EOF' 2>&1
import json, sys
sys.path.insert(0, "scripts")
import claude_cre333_agent as C
rows = [json.loads(x) for x in open("devk1f/creative_F.jsonl", encoding="utf-8") if x.strip()]
last = [r for r in rows if r.get("last")]
print(len(last), sum(r["reply"] == C.FALLBACK for r in last), sum(not r["reply"].strip() for r in last))
EOF
)
set -- $fb x x x; NL=$1; NF=$2; NE=$3
rp "DEV gate: rc $rc; [382/creative/F] lines $n (want 40); adapter line $ad; lfm writer line with @0f604ada $wr; last-request rows $NL, fallback $NF (at most 2), empty $NE (want 0)"
[ "$rc" = 0 ] && [ "$n" = 40 ] && [ "$ad" -ge 1 ] && [ "$wr" -ge 1 ] && [ "$NF" -le 2 ] 2>/dev/null && [ "$NE" = 0 ] || fail "DEV-FAIL (see report.txt and W/logdevF.txt)"
st DEV-OK

# 6. the arms, each launched ONCE with its own log; V1 on each log as soon as its first "[382/creative/" line appears
mkdir -p outF
launch() {
  case $1 in
    F) env K1F_WRITER_MODEL="$L12DIR" K1F_DRAFTS=$TR/outF/drafts_F.jsonl SLEEP02C_ADAPTER="$AD" python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $P --arm claude_k1f_cre:build_null_k1f --name F --model NULL --gen-model "$BASE" --out outF > W/logF.txt 2>&1 &
       ;;
    K) env -u K1F_WRITER_MODEL K1F_DRAFTS=$TR/outF/drafts_K.jsonl SLEEP02C_ADAPTER="$AD" python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $P --arm claude_k1f_cre:build_null_k1a_log --name K --model NULL --gen-model "$BASE" --out outF > W/logK.txt 2>&1 &
       ;;
    T) env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL -u K1F_DRAFTS python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $P --arm twin --name T --model "$BASE" --gen-model "$BASE" --out outF > W/logT.txt 2>&1 &
       ;;
    Q) env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL -u K1F_DRAFTS python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $P --arm twin --name Q --model "$Q2DIR" --gen-model "$Q2DIR" --out outF > W/logQ.txt 2>&1 &
       ;;
    L) env -u SLEEP02C_ADAPTER -u K1F_WRITER_MODEL -u K1F_DRAFTS python -B scripts/claude_twinb_wrap.py scripts/claude_panel382_run.py --panel creative --panel-dir $P --arm twin --name L --model "$L12DIR" --gen-model "$L12DIR" --out outF > W/logL.txt 2>&1 &
       ;;
  esac
  eval "PID_$1=$!"; eval "T0_$1=$(date +%s)"; echo "arm $1 $!" >> W/pids.txt; st "LAUNCH $1 pid $!"
}
killarms() { local x q; for x in $ARMS_UP; do eval "q=\$PID_$x"; kill "$q" 2>/dev/null && st "KILLED $x pid $q"; done; }
v1() { local a=$1 p f w why; eval "p=\$PID_$a"; f=W/log$a.txt
  for w in $(seq 1 180); do grep -q '^\[382/creative/' "$f" 2>/dev/null && break; kill -0 "$p" 2>/dev/null || break; sleep 10; done
  why=""
  grep -q 'refusing to load' "$f" && why="refusing to load"
  case $a in
    F) grep -q "mu402: adapter loaded = $AD" "$f" || why="$why; no adapter line"
       grep '^k1f: creative writer = install_creative_k1f; writer = lfm' "$f" | grep -q '@0f604ada' || why="$why; no lfm writer line with @0f604ada"
       grep -q 'k1a:' "$f" && why="$why; a k1a: line";;
    K) grep -q "mu402: adapter loaded = $AD" "$f" || why="$why; no adapter line"
       grep -q 'k1a: creative writer = install_creative_k1a' "$f" || why="$why; no k1a writer line"
       grep -q 'k1f:' "$f" && why="$why; a k1f: line";;
    *) grep -q 'twinb: the plain twin is Twin336b' "$f" || why="$why; no Twin336b line"
       grep -qE 'mu402:|k1a:|k1f:' "$f" && why="$why; a mu402:, k1a: or k1f: line";;
  esac
  rp "V1 $a: $( [ -z "$why" ] && echo ok || echo "FAIL${why}" )"
  [ -z "$why" ] || { killarms; fail "V1-FAIL $a:$why"; }
}
reap() { local a p t0 t1 rc n; for a in "$@"; do eval "p=\$PID_$a; t0=\$T0_$a"; wait "$p"; rc=$?; t1=$(date +%s)
  n=$(grep -c "^\[382/creative/$a\] " W/log$a.txt)
  st "EXIT $a pid $p rc $rc"; rp "arm $a: rc $rc; [382/creative/$a] lines $n (want 100); wall $(( (t1 - t0 + 30) / 60 )) min"
  eval "RC_$a=$rc"; done; }
ARMS_UP=""
if [ "${TOTMB:-0}" -ge 30000 ] 2>/dev/null; then
  rp "arms: all five at once (${TOTMB} MiB)"
  for a in F K T Q L; do launch $a; ARMS_UP="$ARMS_UP $a"; done
  for a in F K T Q L; do v1 $a; done
  reap F K T Q L
else
  rp "arms: K, F, T first, then Q, L (${TOTMB:-?} MiB)"
  for a in K F T; do launch $a; ARMS_UP="$ARMS_UP $a"; done
  for a in K F T; do v1 $a; done
  reap K F T; ARMS_UP=""
  for a in Q L; do launch $a; ARMS_UP="$ARMS_UP $a"; done
  for a in Q L; do v1 $a; done
  reap Q L
fi
for a in F K T Q L; do eval "rc=\$RC_$a"; [ "$rc" = 0 ] || fail "arm $a exited rc $rc (see W/log$a.txt)"; done
st ARMS-OK

# 7. the three scorers (counts only)
python -B scripts/claude_panel382_run.py --panel creative --panel-dir $P --score outF --names F,K,T,Q,L > W/score.txt 2>&1 || fail "score step (see W/score.txt)"
python -B scripts/claude_k1f_score.py --dedupe outF > W/dedupe.txt 2>&1 || fail "dedupe step (see W/dedupe.txt)"
python -B scripts/claude_k1f_score.py --draft-packet outF --panel $P/items.jsonl > W/draftpacket.txt 2>&1 || fail "draft-packet step (see W/draftpacket.txt)"
st SCORED

# 8. "\r\n" counts (bytes only; expected 0)
python - > W/crlf.txt 2>&1 <<'EOF'
import pathlib
tot = 0
for d in ("outF", "devk1f"):
    for p in sorted(pathlib.Path(d).rglob("*")):
        if p.is_file():
            n = p.read_bytes().count(b"\r\n"); tot += n
            print(p, n)
print("total", tot)
EOF
rp "CRLF: $(tail -1 W/crlf.txt)"
rp "peak GPU memory (15 s samples): $(cat W/gpumem-peak.txt 2>/dev/null)"
rp "end $(date -u +%FT%TZ)"
fin DONE 0
