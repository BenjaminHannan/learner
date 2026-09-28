BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes; eval only). TIME CAP: 240 minutes. LABEL: ks-2-blend.
DISK: 2 (checkpoints, about 7 MB per net, up to 9 nets per seed, stay local in $HOME/premonition-ks and are never pushed)
Owner job (Director helper "keep old skills", Claude, wrote this on 2026-09-28 for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported. The ruler's holdout is never opened; dev panels only.
WHY: artifacts/claude-dir-ks-20260928/PASSMARKS.md (committed before any run). You run sealed code; never edit it. If something breaks, print the first traceback verbatim, run nothing further, exit non-zero (STOP RULE).
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-ks; A=artifacts/claude-dir-ks-20260928
SRC=${KS_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 KS_SRC="$SRC" KS_NETS="$W/nets"
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" cat-file -e "origin/main:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: origin/main has no $A/SEAL-code.sha256.txt"; exit 5; }
mkdir -p "$W" && git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/runs/qual-loop-s$S/source.pt" ] && [ -f "$SRC/runs/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/runs/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/logs
run2() { xargs -P 2 -I{} sh -c 'L=$(echo "{}" | tr " -" "__"); '"$PY"' scripts/claude_dir_ks_run.py {} > '"$A"'/logs/$L.log 2>&1 || echo "FAILED {}"'; }
for S in 0 1; do [ -f "$KS_NETS/loop-s$S-pre/k64.pt" ] && [ -f "$KS_NETS/loop-s$S-pre/k16384.pt" ] || { echo "WAITING: run ks-1-lead0 first (no nets for seed $S)"; exit 5; }; done
printf '%s\n' "blend --seed 0 --k 64" "blend --seed 1 --k 64" "blend --seed 0 --k 16384" "blend --seed 1 --k 16384" | run2
printf '%s\n' "frows --seed 0" "frows --seed 1" | run2
for f in s0-k64 s1-k64 s0-k16384 s1-k16384; do [ -f $A/blend/$f.json ] || echo "MISSING blend $f (see $A/logs)"; done
$PY - <<'KSPY'
import json
for s in (0, 1):
    for k in (64, 16384):
        try:
            r = json.load(open(f"artifacts/claude-dir-ks-20260928/blend/s{s}-k{k}.json"))
        except FileNotFoundError:
            continue
        print("s%d k%d a_star %.1f at_astar %s" % (s, k, r["a_star"], r["at_astar"]))
        print("  P", r["P_full"]); print("  A", r["A_full"])
        for a, v in r["grid"].items():
            print("  a", a, v, "store", r["store"][a])
    try:
        f = json.load(open(f"artifacts/claude-dir-ks-20260928/frows/s{s}.json"))
    except FileNotFoundError:
        continue
    for k, v in f["rungs"].items():
        print("frows s%d k%s" % (s, k), None if v is None else {x: v[x] for x in ("a_star", "blend9", "unblended9")})
KSPY
mkdir -p "$G/$A"; for d in prep lead0 blend frows sleeps logs; do [ -d $A/$d ] && { mkdir -p "$G/$A/$d"; cp -R $A/$d/. "$G/$A/$d/"; }; done
cp $A/selftest.json $A/seal-check.log "$G/$A/" 2>/dev/null
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, dev panels only): the printed lines for each blend record (a*, P, A, every a of the grid with its store score) and the frows lines (a*, blend9, unblended9 per rung; any missing rung). Do not compute a verdict.
PUSH: artifacts/claude-dir-ks-20260928/blend artifacts/claude-dir-ks-20260928/frows artifacts/claude-dir-ks-20260928/logs
