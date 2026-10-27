BASH-ONLY: yes
GPU: no. Mac CPU, strict fp32, one thread each seed. LOAD-LIGHT: yes (about 4 minutes per seed at 2 threads on a container; a few minutes on the Mac). $0, no rental. DISK: 1
Owner job (relation-net thread, Claude). Follow handoff/director-briefs/thread-helper-common.md. Scores the two practised relation nets (artifacts/claude-relnet-eq-20260928/runs/relnet-s{0,1}/source.pt, sha256 b2988e2a... and 115f2451...) on the untouched source guard and writes source.json (schema of claude_sparse_practice.py) with scripts/claude_relnet_eq_guard_srconly.py, which needs no resume.pt. No training, no maze scored, no panel other than the source guard read. Stops with SOURCE-PT-MISMATCH if a source.pt is not the recorded file. Pass (PASSMARKS-C.md "Source guard"): at least 190 of 200 on 4-digit sums and on 5x5 grids and every 2-D weight matrix with a nonzero gradient, in both seeds; if either fails, report it and stop (no maze run).
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
date -u; echo "job $(basename "$0" .bo.sh)"
for i in 1 2 3 4; do git fetch -q origin main && break; echo "git fetch failed (try $i)"; sleep $((2**i)); done
A=artifacts/claude-relnet-eq-20260928
for f in $A/ADDENDUM-1.md $A/checkpoints-sha256.txt scripts/claude_relnet_eq_guard_srconly.py $A/runs/relnet-s0/source.pt $A/runs/relnet-s1/source.pt; do
  git cat-file -e "origin/main:$f" 2>/dev/null || { echo "WAITING: $f is not on origin/main"; exit 5; }
done
D=$(mktemp -d); echo "tree $D"
git archive origin/main scripts $A | tar -x -C "$D"
( cd "$D/$A" && shasum -a 256 -c checkpoints-sha256.txt ) || { echo "SOURCE-NETS-MISMATCH"; exit 6; }
for S in 0 1; do
  rm -f "$D/$A/runs/relnet-s$S/source.json"
  ( cd "$D/scripts" && $PY claude_relnet_eq_guard_srconly.py --seed $S --out "$D/$A/runs/relnet-s$S" --threads 1 ) || { echo "GUARD-FAILED seed $S"; exit 7; }
done
for S in 0 1; do
  mkdir -p "$A/runs/relnet-s$S"; cp "$D/$A/runs/relnet-s$S/source.json" "$A/runs/relnet-s$S/source.json"
  echo "source.json seed $S: $(shasum -a 256 "$A/runs/relnet-s$S/source.json" | cut -c1-16)"
done
python3 -c "
import json
ok=True
for s in (0,1):
    d=json.load(open('artifacts/claude-relnet-eq-20260928/runs/relnet-s%d/source.json'%s))
    print('seed',s,{k:v['right'] for k,v in d['old'].items()},'v1_pass',d['v1_pass'],'gradient_nonzero_all',d['gradient_check']['nonzero_all'],'fixed_depth',d['fixed_depth'])
    ok&=d['v1_pass'] and d['gradient_check']['nonzero_all']
print('SOURCE GUARD', 'PASS in both seeds' if ok else 'FAIL: report, no maze run')
"
rm -rf "$D"; [ -d "$D" ] && echo "temp dir NOT removed" || echo "temp dir removed"
```
PUSH: artifacts/claude-relnet-eq-20260928/runs/relnet-s0/source.json artifacts/claude-relnet-eq-20260928/runs/relnet-s1/source.json
