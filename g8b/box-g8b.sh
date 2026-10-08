# 8b box (g8b/README.md, 2026-10-08): the 8a box script (results/8a-probe/box-probe.sh on claude/project-thread-yha868) with four changes:
#  1. OVL (required) = a commit of this branch: g8b/overlay/custom_io/** is fetched from it and copied over the pinned code (job.py allows eg_embed for B2-only jobs).
#  2. EG=1 (default): transformers $TFVER (default 5.19.0), EmbeddingGemma 2 at its pinned revision into $J/eg2, `python -m custom_io.models.eg check cuda` must be ok.
#  3. B2X values true/false become JSON booleans (B2X=eg_embed:true).
#  4. CK=0 by default (no checkpoint printing: it keeps the box up for hours); END_SLEEP 1800.
# Runs on a Vast GPU box as `bash -c "$(this file)" cio`.
# MODE=job: one rung x seed (custom_io.g8a.job in Vast mode: pool, global caps, arms B2 PT LLM one after another; every folder is printed into the log
#           as RBEGIN/R|/REND base64 lines with a sha256). Needs RUNG, SEED. The own text and web slices are rebuilt and hash-checked by custom_io.g8a.get_data.
# MODE=speed: the speed probe (custom_io.g8a.speed, all rungs and arms + pythia-31m), printed the same way.
# Code: the build branch at a pinned commit; skills data: q33's 200k seed-1 build with its hash check. MAXH = hours of uptime after which every run is
# killed (cost cap); JOBH = hours after which job.py starts no new arm. No credential is on the box.
# Web rows are cut from the 30M slice (the 10M slice is its prefix, nested): the 10M slice's cloze rows come out 1.74M pieces short of the 37.2M budget.
set -u
J=/job; mkdir -p $J/out $J/res $J/w; cd $J
BR=claude/project-thread-f1to6a
PIN=50ee17163276061255e76b1a0039951b5de223b5
OWNSHA=e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0
DPREF=${DPREF:-da1a59cf917f8a5fece264516ce069d4ca45a652}   # data-pool commit the 3M boxes fetched (before the 30M slice grew)
R=https://github.com/BenjaminHannan/learner
ARMS=${ARMS:-}; B2X=${B2X:-}; LRS=${LRS:-1.0}; CK=${CK:-0}; OVL=${OVL:?OVL commit required}; EG=${EG:-1}; PACE=${PACE:-100}; CKWAIT=${CKWAIT:-300}; MODE=${MODE:-job}; RUNG=${RUNG:-3M}; SEED=${SEED:-0}; TFVER=${TFVER:-5.19.0}; MAXH=${MAXH:-6}; JOBH=${JOBH:-5}; DPH=${DPH:-0}
END_SLEEP=${END_SLEEP:-1800}; FAIL_SLEEP=${FAIL_SLEEP:-1200}
T0=$(date +%s)
say() { echo "=== $* $(date -u +%FT%TZ)"; }
die() { say "G8-FAIL $*"; sleep $FAIL_SLEEP; exit 1; }
emit() { emitd $J/w $1; }
emitd() {  # base name : print folder base/name (no checkpoints) as base64 lines
  n=$2; T=$J/res/$n.tgz
  tar -czf $T --exclude='*.pt' --exclude='stdout.txt' -C $1 $n 2>/dev/null
  h=$(sha256sum $T | cut -c1-64)
  echo "RBEGIN|$n|$h|$(stat -c %s $T)"; base64 -w 300 $T | sed "s/^/R|$n|/"; echo "REND|$n"
}
say "G8 START mode $MODE rung $RUNG seed $SEED"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; nproc; df -h $J | tail -1
( while sleep 60; do
    if [ $(( $(date +%s) - T0 )) -ge $(awk "BEGIN{print int($MAXH*3600)}") ]; then say "G8 MAXH $MAXH h reached: killing every run"; pkill -f '^[^ ]*python[0-9.]* -m custom_io'; break; fi
  done ) &
cat > $J/fetch.py <<'PYEOF'
# Download part of a public GitHub commit without git: the commit's tree from the API, then each file from raw.githubusercontent.com.
# python fetch.py REF DEST [--inc PREFIX ...] [--top DIR ...] [--exc PREFIX ...]   prints the commit sha it fetched
import json, os, sys, time, urllib.error, urllib.request
REPO = 'BenjaminHannan/learner'
def get(url, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'fl8a-box', 'Accept': 'application/vnd.github+json'})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:     # GitHub's unauthenticated API allows 60 calls an hour per IP: wait for the reset
            if k == tries - 1:
                raise
            reset = e.headers.get('X-RateLimit-Reset') if e.code in (403, 429) else None
            wait = min(3900, max(30, int(reset) - int(time.time()) + 5)) if reset else 5 * (k + 1)
            print('fetch: HTTP %d, waiting %d s' % (e.code, wait), file=sys.stderr, flush=True)
            time.sleep(wait)
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))
ref, dest = sys.argv[1], sys.argv[2]
inc, top, exc, cur = [], [], [], None
for x in sys.argv[3:]:
    if x in ('--inc', '--top', '--exc'):
        cur = {'--inc': inc, '--top': top, '--exc': exc}[x]
    else:
        cur.append(x)
c = json.loads(get('https://api.github.com/repos/%s/commits/%s' % (REPO, ref)))
sha = c['sha']
_t = {}
def tree(tsha, rec=False):
    k = (tsha, rec)
    if k not in _t:
        _t[k] = json.loads(get('https://api.github.com/repos/%s/git/trees/%s%s' % (REPO, tsha, '?recursive=1' if rec else '')))
        assert not _t[k].get('truncated'), 'tree listing truncated: ' + tsha
    return _t[k]['tree']
def subtree(path):
    cur = c['commit']['tree']['sha']
    for part in [x for x in path.strip('/').split('/') if x]:
        cur = [e for e in tree(cur) if e['path'] == part and e['type'] == 'tree'][0]['sha']
    return cur
want = {}
for p in inc:
    base = p.strip('/')
    for e in tree(subtree(base), True):
        if e['type'] == 'blob':
            want[base + '/' + e['path']] = e['size']
for d in top:
    for e in tree(subtree(d)):
        if e['type'] == 'blob':
            pre = d.strip('/')
            want[(pre + '/' if pre else '') + e['path']] = e['size']
want = [dict(path=k, size=v) for k, v in sorted(want.items()) if not any(k.startswith(x) for x in exc)]
assert want, 'nothing matched'
def one(e):
    p = os.path.join(dest, e['path'])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    b = get('https://raw.githubusercontent.com/%s/%s/%s' % (REPO, sha, e['path']))
    assert len(b) == e['size'], (e['path'], len(b), e['size'])
    open(p, 'wb').write(b)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex:
    list(ex.map(one, want))
print(sha, len(want), 'files')
PYEOF
python $J/fetch.py $PIN mine --inc custom_io --exc custom_io/results/ > $J/out/fetch_mine.txt || die fetch-mine
[ "$(cut -d' ' -f1 $J/out/fetch_mine.txt)" = "$PIN" ] || die pin-check
say "code at $PIN"
python $J/fetch.py $OVL ovl --inc g8b/overlay > $J/out/fetch_ovl.txt || die fetch-ovl
[ "$(cut -d' ' -f1 $J/out/fetch_ovl.txt)" = "$OVL" ] || die ovl-pin-check
cp -rv ovl/g8b/overlay/custom_io/. mine/custom_io/ || die overlay
say "overlay at $OVL"
python $J/fetch.py claude/project-thread-y0sxwe cur --inc skills_curriculum || die fetch-cur
(cd cur && python -m skills_curriculum.build --out $J/data --train 200000 --dev-per-cell 40 --seed 1 > $J/out/build.log 2>&1) || die build
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$J/data/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
(cd cur && python -m skills_curriculum.build --out $J/data_big --train 200000 --dev-per-cell 200 --seed 1 > $J/out/build_big.log 2>&1) || die build-big
[ "$(sha256sum $J/data/train.jsonl | cut -c1-64)" = "$(sha256sum $J/data_big/train.jsonl | cut -c1-64)" ] || die big-train-hash
echo "big build train.jsonl hash matches"
PIP_BREAK_SYSTEM_PACKAGES=1 pip install -q --break-system-packages "transformers==$TFVER" "safetensors==0.8.0" accelerate numpy pyarrow huggingface_hub > out/pip.log 2>&1 || { tail -3 out/pip.log; die pip; }
python -c "import torch, transformers, pyarrow; print(torch.__version__, transformers.__version__, pyarrow.__version__, torch.cuda.get_device_name(0))"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 PYTHONUNBUFFERED=1
if [ "$EG" = 1 ]; then
  (cd mine && python -c "from huggingface_hub import snapshot_download as s; from custom_io.models.eg import EG_ID, EG_REV; s(EG_ID, revision=EG_REV, local_dir='$J/eg2')") > out/eg_dl.log 2>&1 || { tail -5 out/eg_dl.log; die eg-download; }
  export CUSTOM_IO_EG2=$J/eg2
  (cd mine && python -m custom_io.models.eg check cuda) || die eg-check
  say "EmbeddingGemma 2 ready"
fi
if [ "$MODE" = speed ]; then
  say "G8 SPEED START"
  (cd mine && python -m custom_io.g8a.speed --data $J/data --out $J/w/8a-speed --public pythia31m --mem-gb 15 --updates 200 --dph $DPH > $J/w/8a-speed.stdout.txt 2>&1)
  rc=$?; mkdir -p $J/w/8a-speed; cp $J/w/8a-speed.stdout.txt $J/w/8a-speed/probe.log; tail -40 $J/w/8a-speed.stdout.txt
  emit 8a-speed; say "G8 DONE speed rc=$rc"
else
  python $J/fetch.py $DPREF data-pool --inc data_pool/built data_pool/panels --top data_pool || die fetch-data-pool
  python $J/fetch.py claude/8a-own-data own-data --top "" || die fetch-own-data
  say "G8 DATA START"
  (cd mine && python -m custom_io.g8a.get_data --work $J --data-pool $J/data-pool --own-xz $J/own-data --expect-manifest-sha $OWNSHA) || die get-data
  say "G8 DATA READY"
  B2JSON=$(python -c "import json,sys; V=lambda v: {'true': True, 'false': False}.get(v, float(v) if '.' in v else int(v) if v.lstrip('-').isdigit() else v); print(json.dumps({k: V(v) for k, v in (x.split(':') for x in sys.argv[1].split(',') if x)}))" "$B2X")
  say "G8 B2 extra $B2JSON arms ${ARMS:-all} lr-scale $LRS"
  (cd mine && python -m custom_io.g8a.job --rung $RUNG --seed $SEED ${ARMS:+--arms $ARMS} --b2-extra "$B2JSON" --lr-scale $LRS --work $J/g8a --skills $J/data --big-data $J/data_big --data8a $J/data8a --web $J/data8a/web/slice_rung30.jsonl --maxh $JOBH --dph $DPH)
  say "G8 DONE job rc=$?"
  if [ "$CK" = 1 ]; then
    # Checkpoints off the box through the log (same format as the reader branch's box/ck_export.sh, read by vast.py collectck):
    # each checkpoint.pt is tar.gz'd as 8a-RUNG/sSEED-ARM/checkpoint.pt, split into 3 MB parts, one part printed every PACE s.
    sleep $CKWAIT; N=0
    for c in $J/g8a/w/8a-$RUNG-s$SEED-*/checkpoint.pt; do
      [ -f "$c" ] || continue
      run=$(basename $(dirname $c)); run=${run#8a-$RUNG-}
      mkdir -p $J/ck/8a-$RUNG/$run; ln -f $c $J/ck/8a-$RUNG/$run/checkpoint.pt
      T=$J/res/ck-$run.tgz; tar -czf $T -C $J/ck 8a-$RUNG/$run/checkpoint.pt
      full=$(sha256sum $T | cut -c1-64); rm -f $J/res/ck-$run.part.*; split -b 3000000 -d -a 3 $T $J/res/ck-$run.part.
      n=$(ls $J/res/ck-$run.part.* | wc -l); echo "CKFULL|8a-$RUNG/$run|$full|$n"
      for p in $(ls $J/res/ck-$run.part.* | sort); do
        k=$((10#${p##*.})); N=$((N + 1)); h=$(sha256sum $p | cut -c1-64)
        echo "RBEGIN|ck$N|$h|$(stat -c %s $p)|8a-$RUNG/$run|$k|$n"; base64 -w 480 $p | sed "s/^/R|ck$N|/"; echo "REND|ck$N"
        echo "part ck$N 8a-$RUNG/$run $k/$n"; sleep $PACE
      done
    done
    echo "CKDONE|$N"
    for d in $J/g8a/w/8a-$RUNG-s$SEED-*; do emitd $J/g8a/w $(basename $d); sleep 20; done    # re-print results (the first print is buried)
    say "G8 CK DONE $N parts"
  fi
fi
sleep $END_SLEEP
