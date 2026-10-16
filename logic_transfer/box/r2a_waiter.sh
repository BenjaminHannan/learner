#!/bin/bash
# Recipe 2 replica box: collect, verify, commit, push, re-fetch, THEN destroy (Opus gate change 4; MARKS-LT2 Addendum 11 section 5). No credential in this file: the Vast key and the
# GitHub access come from the environment's proxy. usage: bash r2a_waiter.sh BOXID WORKDIR     (re-run it if it is killed: collectck keeps what it already saved)
# The box is destroyed ONLY at the end, and only if every step before it succeeded; any failure leaves the box up (MAXH is the backstop: it ends itself 20 minutes after MAXH hours).
set -u
ID=$1; W=$2; REPO=$(cd "$(dirname "$0")/../.." && pwd); V="python3 $REPO/custom_io/box/vast.py"
BRANCH=claude/lt2-r2a-replica-checkpoints; SUB=logic_transfer/replicas/r2a
RUNS=${RUNS:-"s200-s1 s200-s2 s201-s1 s201-s2 s204-s1 s204-s2"}
WANT=""; for r in $RUNS; do WANT="$WANT rung6/$r"; done; WANT="$WANT lt2-rung6"
mkdir -p $W/collected; LOG=$W/waiter.log
say() { echo "=== $* $(date -u +%FT%TZ)" | tee -a $LOG; }
fail() { say "WAITER FAIL: $* (box $ID NOT destroyed)"; echo "$*" > $W/ATTENTION.txt; exit 1; }
say "WAITER START box $ID want:$WANT"
complete() { for r in $RUNS; do [ -f $W/collected/rung6/$r/checkpoint.pt ] || return 1; done; [ -d $REPO/custom_io/results/lt2-rung6 ]; }   # collectck also returns when --max-min ran out: look at the files
until [ -f $W/COLLECTED ]; do
  $V collectck --id $ID --out $W/collected --want "$WANT" --max-min 100 >> $W/collect.log 2>&1
  tail -n 1 $W/collect.log | cut -c1-300 | tee -a $LOG
  if complete; then touch $W/COLLECTED; else
    $V status --id $ID 2>&1 | tee -a $LOG | grep -q '"cur_state": *null' && { say "box is gone (no instance record)"; break; }
  fi
done
[ -f $W/COLLECTED ] || fail "collectck did not finish (see collect.log)"
say "collected; verifying"
python3 - "$W" $RUNS <<'PY' || fail "verification (load / sha) failed"
import hashlib, json, sys, pathlib, torch
W, runs = pathlib.Path(sys.argv[1]), sys.argv[2:]
out = {}
for r in runs:
    f = W / 'collected' / 'rung6' / r / 'checkpoint.pt'
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    rec = (W / 'collected' / ('rung6__' + r + '.sha256')).read_text()
    assert h in rec and '(box: ' + h in rec, (r, 'box-side file sha was not matched', rec)
    ck = torch.load(f, map_location='cpu', weights_only=False)
    assert sorted(ck) == ['cfg', 'chars', 'model', 'name', 'step'], (r, sorted(ck))
    out[r] = dict(sha256=h, bytes=f.stat().st_size, step=int(ck['step']))
json.dump(out, open(W / 'VERIFIED.json', 'w'), indent=1)
print(json.dumps(out)[:600])
PY
say "verified; committing to $BRANCH"
cd $REPO || fail cd
git fetch -q origin main || fail "fetch main"
WT=$W/wt-ck; rm -rf $WT; git worktree prune
if git ls-remote --exit-code --heads origin $BRANCH >/dev/null 2>&1; then git fetch -q origin $BRANCH && git worktree add -q -B $BRANCH $WT FETCH_HEAD || fail "worktree"; else git worktree add -q -b $BRANCH $WT origin/main || fail "worktree"; fi
mkdir -p $WT/$SUB
for r in $RUNS; do mkdir -p $WT/$SUB/$r; cp -p $W/collected/rung6/$r/checkpoint.pt $WT/$SUB/$r/checkpoint.pt; done
cp -p $W/VERIFIED.json $WT/$SUB/VERIFIED.json
( cd $WT/$SUB && sha256sum */checkpoint.pt > SHA256SUMS )
for d in lt2-rung6 ladder; do [ -d $REPO/custom_io/results/$d ] && { mkdir -p $WT/$SUB/result/$d && cp -rp $REPO/custom_io/results/$d/. $WT/$SUB/result/$d/; }; done   # the rung-6 result block: per-run eval.jsonl, run.json, log.jsonl, stop.json, summary
cp -p $W/waiter.log $W/collect.log $WT/$SUB/ 2>/dev/null
( cd $WT && git add -A $SUB && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "LT-2 Recipe 2: the six R2a replica checkpoints (sealed code, box $ID), sha256-checked against the box, plus the rung-6 result block

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MGuNX8XfxJSDVAJZ9TXxyz" ) || fail "commit"
for i in 1 2 3 4; do ( cd $WT && git push -q -u origin $BRANCH ) && break; sleep $((2 ** i)); [ $i = 4 ] && fail "push"; done
say "pushed; re-fetching from GitHub to compare"
git fetch -q origin $BRANCH || fail "refetch"
for r in $RUNS; do
  a=$(git show FETCH_HEAD:$SUB/$r/checkpoint.pt | sha256sum | cut -c1-64); b=$(sha256sum $W/collected/rung6/$r/checkpoint.pt | cut -c1-64)
  [ "$a" = "$b" ] || fail "re-fetched $r differs from the collected file ($a vs $b)"
done
say "re-fetched files match; destroying box $ID"
$V destroy --id $ID 2>&1 | tee -a $LOG
$V credit 2>&1 | tee -a $LOG
touch $W/DESTROYED; say "WAITER DONE (box $ID destroyed after push + re-fetch match)"
