#!/bin/bash
# accept.py: the ACCEPT branch (a copy of the CPU smoke result with steps edited to 24000) and two REJECT branches (mismatch above 0.1 %, wrong parameter count)
SRC=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox/fake_out/collect/8aPTC3S-3M-s400
T=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox/accept_t
KIT=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
rm -rf $T; mkdir -p $T
mk() {   # name, python edit of the arm result r
  cp -r $SRC $T/$1
  python3 -I -c "
import json
p = '$T/$1/PTC/RESULT.json'
r = json.load(open(p))
$2
json.dump(r, open(p, 'w'))
"
}
mk good "r['steps'] = 24000"
mk mismatch "r['steps'] = 24000; r['cap_hits']['calc_mismatch'] = 40; r['cap_hits']['calc_rows'] = 32000"
mk params "r['steps'] = 24000; r['n_params'] = 4023377"
for n in good mismatch params; do
  python3 -I $KIT/accept.py $T/$n > $T/$n.out; echo "$n exit=$?  $(grep -E '^(ACCEPT|REJECT)' $T/$n.out)"
done
