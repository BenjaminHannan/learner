#!/bin/bash
# y1t vast helper, run on the rental (Linux, root) by handoff/kit/y1tvast/pass.sh over ssh (Answering-from-memory
# thread, 2026-09-27; ADDENDUM-9). Linux counterpart of handoff/kit/y1tpc/remote/boy1t.sh. It reaches the rental inside
# the tree streamed from the pinned commit, and pass.sh checks its sha256 before using it (never piped into bash).
# Actions: kithash | mark-tree PIN | setup-start | setup-run (started by setup-start only) | state | checks |
#          launch-chain CHAINCAP | stop-chain REASON | manifest | pack
# It never edits sealed code and never starts the chain a second time (W/chain.started). The only process ever stopped
# is the chain's own running step, by the exact PID chain.sh started (stop-chain asks chain.sh to do it).
set -u
export PATH=/opt/conda/bin:$PATH   # the pytorch image's python lives here; an ssh command may not have it on PATH
B=${BVY1T:-$HOME/tree}
A=artifacts/claude-y1t-20260926
I=$A/glm2/items
KR=handoff/kit/y1tvast/remote
MINICPM=87179e5c1f455ef22e6223592d2d61351b525bfc
# the files copied back to the Mac (pass.sh maps each to its place under run/); tr/adapter398r.pt goes to the Mac only
COLLECT="$I/drafts.jsonl $I/train.jsonl $I/dev.jsonl $I/drafts_summary.json tr/train398r.json tr/adapter398r.pt
 eval/y1g_rows.jsonl eval/y1g_summary.json eval_plain/y1g_rows.jsonl eval_plain/y1g_summary.json
 W/drafts_log.txt W/train_log.txt W/eval_log.txt W/eval_plain_log.txt W/steps.txt W/checks.txt W/gpu_log.txt
 W/setup_log.txt W/chain_log.txt W/pids.txt
 h1/rows_A.jsonl h1/rows_B.jsonl W/h1_A_log.txt W/h1_B_log.txt"
cd "$B" 2>/dev/null || { echo "ERR no folder $B"; exit 3; }

freegb() { df -BG --output=avail "$B" | tail -1 | tr -dc '0-9'; }
gpu() { timeout 20 nvidia-smi --query-gpu=memory.used,memory.total,power.draw --format=csv,noheader,nounits 2>/dev/null | tr -d ' ' | tr ',' ' ' | head -1; }
age() { [ -e "$1" ] && echo $(( ( $(date +%s) - $(stat -c %Y "$1") ) / 60 )) || echo -1; }
# processes by their command line, read from /proc (the image may have no ps or pgrep): "pid args" lines matching $1
pmatch() { local d c; for d in /proc/[0-9]*; do c=$( { tr '\0' ' ' < "$d/cmdline"; } 2>/dev/null ) || continue; [ -n "$c" ] && echo "${d#/proc/} $c"; done | grep -E "$1" | grep -v -E '^[0-9]+ (grep|tr) ' ; }
procs() { pmatch 'claude_(y1t_data|bm398r_train|y1g_doubt|y1t_h1run)\.py' | grep -v 'bov\.sh' ; }
# a selftest counts only with rc=0 AND its own pass line (claude_bm398r_train.py selftest exits 0 even when it prints FAIL)
# the fifth check, IMPORTS OK, imports every package the four step scripts can reach (ADDENDUM-11: p1's train step died on
# a lazy 'import nltk' that no selftest reached)
OKRE='^CHECK [^ ]+ rc=0 (selftest ok|BM398R-TRAIN-SELFTEST PASS|IMPORTS OK)'
pyenv() { PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 "$(cat W/python.txt)" -B "$@"; }

setup_run() {
  # env-only setup (rent kit section C with the TORCH VERSION / TORCH UPGRADE rules); W/setup.done gets rc=0 or the
  # number of the step that failed. Nothing in the tree is changed.
  fail() { echo "SETUP-FAIL step $1: $2"; echo "rc=$1 $2" > W/setup.done; exit 0; }
  echo "setup start $(date -u +%FT%TZ)"
  local f py base
  f=$(freegb); echo "DISK $f GB free"
  [ "${f:-0}" -ge 20 ] || fail 11 "under 20 GB free"
  py=$(command -v python || command -v python3)
  [ -n "$py" ] || fail 12 "no python"
  echo "PYTHON $py $("$py" -V 2>&1)"
  if [ "${MOCKY1T:-0}" = 1 ]; then
    echo "MOCK: no apt, no pip, no download"; base=${BASEY1T:-/nonexistent}
  else
    # y1g's rental needed gcc for triton kernels; install it only if missing (environment, not code)
    command -v gcc >/dev/null || { apt-get update -qq >/dev/null 2>&1; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gcc >/dev/null 2>&1; }
    echo "GCC $(gcc --version 2>/dev/null | head -1)"
    # BensPC's versions (torch 2.11.0+cu128, transformers 5.17.0); --no-cache-dir keeps the disk free
    "$py" -m pip install -q --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 || fail 13 "torch 2.11.0"
    "$py" -m pip uninstall -y -q torchvision torchaudio >/dev/null 2>&1
    "$py" -m pip install -q --no-cache-dir transformers==5.17.0 safetensors huggingface_hub accelerate numpy || fail 14 "transformers 5.17.0"
    # the scorer claude_bm390_score.py (imported inside claude_bm398r_train.py's DEV check) needs nltk and regex; nltk at the
    # version of the venv that recounted bm390 (recount3/recount.md); pyarrow is reachable from claude_bm390.py (ADDENDUM-11)
    "$py" -m pip install -q --no-cache-dir nltk==3.10.3 regex pyarrow || fail 18 "nltk 3.10.3, regex, pyarrow"
    "$py" -c 'import torch, transformers; assert torch.cuda.is_available(); x = torch.ones(4, device="cuda"); print("IMPORT-OK", torch.__version__, torch.version.cuda, transformers.__version__, float(x.sum()))' || fail 15 "import check"
    # the only model: plain MiniCPM5-1B at the commit every y1 run used (Ben's yes 2026-09-23)
    base=$(HF_HUB_OFFLINE=0 "$py" -c "from huggingface_hub import snapshot_download as s; print(s('openbmb/MiniCPM5-1B', revision='$MINICPM'))" 2>>W/setup_log.txt | tail -1)
  fi
  case "$base" in */$MINICPM) ;; *) fail 16 "snapshot path '$base' does not end in $MINICPM";; esac
  [ -f "$base/config.json" ] || fail 17 "no config.json in $base"
  echo "$py" > W/python.txt; echo "$base" > W/base.txt
  echo "BASE $base"
  echo "setup end $(date -u +%FT%TZ)"
  echo "rc=0" > W/setup.done
}

state() {
  local P
  echo "PIN $(cat W/tree-pin.txt 2>/dev/null)"
  echo "SETUP started=$([ -f W/setup.started ] && echo 1 || echo 0) $(head -1 W/setup.done 2>/dev/null || echo rc=-)"
  [ -f W/setup_log.txt ] && echo "SETUPLAST age=$(age W/setup_log.txt)m $(tail -c 600 W/setup_log.txt | grep . | tail -1 | cut -c1-200)"
  echo "SEALR $(sha256sum -c $A/SEAL-y1t-rental.sha256.txt 2>/dev/null | grep -c ': OK$') $(grep -c . $A/SEAL-y1t-rental.sha256.txt)"
  echo "SEALH $(sha256sum -c $A/SEAL-y1tH1-runner.sha256.txt 2>/dev/null | grep -c ': OK$') $(grep -c . $A/SEAL-y1tH1-runner.sha256.txt)"
  echo "SEALP $(cd artifacts/claude-spare401-20260926 2>/dev/null && grep ' panel/turns.jsonl$' SEAL-spare401.sha256.txt | sha256sum -c 2>/dev/null | grep -c ': OK$') 1"
  echo "ITEMS $(sha256sum $I/items_train.jsonl | cut -c1-64) $(sha256sum $I/items_dev.jsonl | cut -c1-64)"
  echo "DISK $(freegb)"
  echo "GPU $(gpu)"
  P=$(procs)
  echo "PY $(echo "$P" | grep -c .)"
  echo "$P" | grep . | cut -c1-240 | sed 's/^ */PROCLINE /'
  # the detached setup and chain, so that the Mac can tell a dead one from a slow one
  echo "SETUPPROC $(pmatch 'remote/bov\.sh setup-run' | grep -c .)"
  echo "CHAINPROC $(pmatch 'remote/chain\.sh' | grep -c .)"
  echo "CHECKS $([ -f W/checks.txt ] && grep -Ec "$OKRE" W/checks.txt || echo -) $([ -f W/checks.txt ] && grep -c '^CHECK ' W/checks.txt || echo -)"
  [ -f W/checks.txt ] && grep -E '^(VERSIONS|GPUNAME) ' W/checks.txt | head -2
  echo "CHAIN started=$([ -f W/chain.started ] && echo 1 || echo 0) done=$([ -f W/chain.done ] && echo 1 || echo 0) stopreq=$([ -f W/stop.request ] && echo 1 || echo 0) age=$(age W/chain.started)m"
  [ -f W/steps.txt ] && sed 's/^/STEP /' W/steps.txt
  for f in drafts train eval eval_plain h1_A h1_B; do
    [ -f "W/${f}_log.txt" ] && echo "LAST $f age=$(age "W/${f}_log.txt")m $(tail -c 800 "W/${f}_log.txt" | grep . | tail -1 | cut -c1-200)"
  done
  [ -f tr/adapter398r.pt ] && echo "ADAPTER $(sha256sum tr/adapter398r.pt | cut -c1-64) $(wc -c < tr/adapter398r.pt | tr -d ' ')"
  [ -s W/gpu_log.txt ] && echo "GPULOG $(awk '{n++; if($2+0>m)m=$2+0; if($4+0>p)p=$4+0; l=$0} END{printf "lines=%d peak_used=%d peak_power=%.1f last=%s", n, m, p, l}' W/gpu_log.txt)"
  echo "FILES adapter=$([ -f tr/adapter398r.pt ] && echo 1 || echo 0) merged=$([ -d tr/merged ] && echo 1 || echo 0) eval=$([ -d eval ] && echo 1 || echo 0) eval_plain=$([ -d eval_plain ] && echo 1 || echo 0) h1A=$([ -f h1/rows_A.jsonl ] && echo 1 || echo 0) h1B=$([ -f h1/rows_B.jsonl ] && echo 1 || echo 0)"
  echo "END-STATE"
}

checks() {
  [ -f W/checks.txt ] && { echo "CHECKS already done"; cat W/checks.txt; return 0; }
  [ "$(head -1 W/setup.done 2>/dev/null)" = "rc=0" ] || { echo "REFUSED: setup has not ended rc=0"; return 5; }
  local rc out s
  {
    for s in claude_y1t_data.py claude_y1g_doubt.py claude_y1t_h1run.py; do
      out=$(pyenv scripts/$s --selftest 2>&1); rc=$?
      echo "CHECK $s rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
    done
    out=$(pyenv scripts/claude_bm398r_train.py selftest 2>&1); rc=$?
    echo "CHECK claude_bm398r_train.py rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
    # every module the four step scripts import, at the top or inside a function, followed through the local scripts/ files
    # they import (read with ast, nothing run); then the four scripts and every other module are imported here
    out=$(pyenv - 2>&1 <<'PYEOF'
import ast, importlib, os, sys
sys.path.insert(0, "scripts")
steps = ["claude_y1t_data", "claude_bm398r_train", "claude_y1g_doubt", "claude_y1t_h1run"]
todo, seen, ext = list(steps), set(), set()
while todo:
    m = todo.pop()
    if m in seen:
        continue
    seen.add(m)
    for n in ast.walk(ast.parse(open(os.path.join("scripts", m + ".py")).read())):
        names = []
        if isinstance(n, ast.Import):
            names = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            names = [n.module]
        for x in names:
            if os.path.exists(os.path.join("scripts", x.split(".")[0] + ".py")):
                todo.append(x.split(".")[0])
            elif x != "__future__":
                ext.add(x)
bad = []
for x in steps + sorted(ext):
    try:
        importlib.import_module(x)
    except BaseException as e:
        bad.append("%s (%s: %s)" % (x, type(e).__name__, str(e)[:60]))
if bad:
    print("IMPORTS FAIL " + "; ".join(bad))
    sys.exit(1)
import nltk
print("IMPORTS OK the 4 step scripts, %d local files read, %d other modules imported (nltk %s)" % (len(seen), len(ext), nltk.__version__))
PYEOF
); rc=$?
    echo "CHECK imports rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-200)"
    echo "VERSIONS $(pyenv -c 'import torch, transformers; print(torch.__version__, torch.version.cuda, transformers.__version__)' 2>&1 | tail -1)"
    echo "GPUNAME $(timeout 20 nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1)"
  } > W/checks.tmp
  mv W/checks.tmp W/checks.txt   # only a complete list counts (a cut connection leaves checks.tmp, and checks run again)
  cat W/checks.txt
}

case "${1:-}" in
  kithash) cd "$B/$KR" && sha256sum bov.sh chain.sh ;;
  mark-tree)
    [ -n "${2:-}" ] || { echo "ERR no pin"; exit 4; }
    [ -e W/tree-pin.txt ] && { echo "TREE already marked $(cat W/tree-pin.txt)"; exit 0; }
    mkdir -p W && echo "$2" > W/tree-pin.txt && echo "TREE marked $2" ;;
  setup-start)
    [ -e W/setup.started ] && { echo "SETUP already started $(cat W/setup.started)"; exit 0; }
    mkdir -p W && date -u +%FT%TZ > W/setup.started
    setsid nohup bash "$KR/bov.sh" setup-run >> W/setup_log.txt 2>&1 < /dev/null &
    echo "SETUP started pid=$! $(date -u +%FT%TZ)" ;;
  setup-run) setup_run ;;
  state) state ;;
  checks) checks ;;
  launch-chain)
    [ -e W/chain.started ] && { echo "REFUSED: W/chain.started exists (never a second chain)"; exit 5; }
    [ "$(head -1 W/setup.done 2>/dev/null)" = "rc=0" ] || { echo "REFUSED: setup has not ended rc=0"; exit 5; }
    [ -f W/checks.txt ] || { echo "REFUSED: checks not run"; exit 5; }
    [ "$(grep -Ec "$OKRE" W/checks.txt)" = 5 ] || { echo "REFUSED: not every check passed (5 needed)"; exit 5; }
    [ -z "$(procs)" ] || { echo "REFUSED: a y1t python is running"; exit 5; }
    [ "$(freegb)" -ge 8 ] || { echo "REFUSED: under 8 GB free ($(freegb) GB)"; exit 5; }
    case "${2:-}" in [0-9]*) ;; *) echo "REFUSED: no chain cap"; exit 5;; esac
    echo "$2" > W/chaincap.txt
    setsid nohup bash "$KR/chain.sh" > W/chain_log.txt 2>&1 < /dev/null &
    echo "LAUNCH chain $(date -u +%FT%TZ) rc=0 pid=$! cap=${2}m" ;;
  stop-chain)
    [ -f W/chain.started ] || { echo "NOT-STARTED"; exit 0; }
    [ -f W/chain.done ] && { echo "ALREADY-DONE"; exit 0; }
    [ -f W/stop.request ] || echo "${2:-asked} $(date -u +%FT%TZ)" > W/stop.request
    # chain.sh checks every 30 s, then gives the step 60 s after TERM before KILL
    i=0; while [ ! -f W/chain.done ] && [ $i -lt "${STOPWAITY1T:-36}" ]; do sleep 5; i=$((i+1)); done
    [ -f W/chain.done ] && echo "STOPPED chain.done $(cat W/chain.done)" || echo "STOP-PENDING: no chain.done after $((i*5)) s"
    tail -3 W/steps.txt 2>/dev/null ;;
  manifest) for f in $COLLECT; do [ -f "$f" ] && echo "MAN $(sha256sum "$f" | cut -c1-64) $(wc -c < "$f" | tr -d ' ') $f"; done; echo "END-MAN" ;;
  pack) ls -d $COLLECT 2>/dev/null | tar -cf - -T - ;;
  *) echo "ERR unknown action ${1:-}"; exit 2 ;;
esac
