#!/bin/bash
# offline test of the box script's guard.py (the copy the dry run wrote) on synthetic training logs
# arguments of guard.py: LOG T0 NOW DPH CAP GUARD_STEP STEPS EXTRA_H MAXH
G=/dev/shm/ptcdry/J/guard.py
T=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox/gtest
now=$(date +%s); t0=$((now - 1800))
mk() {
  printf '{"event": "cap_hits", "step": 0}\n{"event": "train", "step": 500, "loss": 3.1, "lr": 0.001, "elapsed": %s, "cap_hits": 0}\n' "$1" > $T/$2
  [ -n "$3" ] && printf '{"event": "train", "step": 1000, "loss": 2.9, "lr": 0.001, "elapsed": %s, "cap_hits": 0}\n' "$3" >> $T/$2
}
mk 220 fast.log 450;   echo "case fast (0.45 s/update, 0.38 USD/h, cap 4, MAXH 6): expect rc 0";            python3 $G $T/fast.log $t0 $now 0.38 4.0 1000 24000 0.5 6; echo "fast rc=$?"
mk 2000 slow.log 4000; echo "case slow (4 s/update): expect rc 3 over the dollar cap";                      python3 $G $T/slow.log $t0 $now 0.38 4.0 1000 24000 0.5 6; echo "slow rc=$?"
mk 1000 mid.log 2000;  echo "case mid (2 s/update, 0.10 USD/h): cheap but 13.5 h > MAXH 6: expect rc 3";    python3 $G $T/mid.log $t0 $now 0.10 4.0 1000 24000 0.5 6; echo "mid rc=$?"
echo "case mid with MAXH 0 (off): expect rc 0";                                                              python3 $G $T/mid.log $t0 $now 0.10 4.0 1000 24000 0.5 0; echo "mid-nomaxh rc=$?"
mk 220 early.log "";   echo "case early (no update 1000 yet): expect rc 4";                                 python3 $G $T/early.log $t0 $now 0.38 4.0 1000 24000 0.5 6; echo "early rc=$?"
echo "case missing log: expect rc 4";                                                                        python3 $G $T/missing.log $t0 $now 0.38 4.0 1000 24000 0.5 6; echo "missing rc=$?"
