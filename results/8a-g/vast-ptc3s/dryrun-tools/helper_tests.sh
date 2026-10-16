#!/bin/bash
# offline tests of the b3sweep helper scripts (at_pick.py, at_report.py, atcmd.py) extracted from the box script: helper_tests.sh [SCRIPT]
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
S=${1:-/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/ptc3s_box.sh}
T=$B/helper_t
rm -rf $T; mkdir -p $T
for f in mkcmd_at atcmd at_report at_pick; do
  awk -v f="$f.py" '$0 ~ "cat > \\$J/" f " <<.PY." {on=1; next} on && $0=="PY" {on=0} on' $S > $T/$f.py
  echo "extracted $f.py: $(wc -l < $T/$f.py) lines, sha256 $(sha256sum $T/$f.py | cut -c1-16)"
done
mk() {   # NAME then python dict literal for points
  python3 - "$T/$1.json" "$2" <<'PY'
import json, sys
pts = eval(sys.argv[2])
json.dump({'sections': {'accumsweep': {'points': {str(k): v for k, v in pts.items()}}}}, open(sys.argv[1], 'w'))
PY
}
P() { python3 -I $T/at_pick.py "$@"; }
echo "--- pick 1: 16 and 8 both fit; 8 is faster -> expect 8"
mk s1 "{32: dict(s_per_update_median=7.2, peak_alloc_gb=1.5, oom=False), 16: dict(s_per_update_median=4.1, peak_alloc_gb=2.9, oom=False), 8: dict(s_per_update_median=3.0, peak_alloc_gb=5.0, oom=False), 4: dict(s_per_update_median=2.9, peak_alloc_gb=11.2, oom=False)}"
P $T/s1.json
echo "--- pick 2: accum 4 is fastest and fits (9.9 GB) -> expect 4"
mk s2 "{32: dict(s_per_update_median=7.2, peak_alloc_gb=1.5, oom=False), 16: dict(s_per_update_median=4.1, peak_alloc_gb=2.9, oom=False), 8: dict(s_per_update_median=3.0, peak_alloc_gb=5.0, oom=False), 4: dict(s_per_update_median=2.0, peak_alloc_gb=9.9, oom=False)}"
P $T/s2.json
echo "--- pick 3: nothing but 32 qualifies (others over 10 GB, OOM or no number) -> expect 8 (the default)"
mk s3 "{32: dict(s_per_update_median=7.2, peak_alloc_gb=1.5, oom=False), 16: dict(s_per_update_median=4.1, peak_alloc_gb=10.4, oom=False), 8: dict(s_per_update_median=None, peak_alloc_gb=None, oom=True), 4: dict(s_per_update_median=None, peak_alloc_gb=3.0, oom=False)}"
P $T/s3.json
echo "--- pick 4: the sweep section failed (an error record, no points) -> expect 8"
echo '{"sections": {"accumsweep": {"error": "boom"}}}' > $T/s4.json; P $T/s4.json
echo "--- pick 5: the file is missing -> expect 8"
P $T/missing.json
echo "--- pick 6: not json -> expect 8"
echo 'not json' > $T/s6.json; P $T/s6.json
echo "--- pick 7: a speed number but memory unknown (CPU run) for every accum -> expect 8"
mk s7 "{32: dict(s_per_update_median=0.5, peak_alloc_gb=None, oom=False), 16: dict(s_per_update_median=0.4, peak_alloc_gb=None, oom=False)}"
P $T/s7.json
echo "--- atcmd: edits --out, the accum and appends --steps / --train-extra; refuses a queue line that is not AT=32"
echo "python -m custom_io.g8a.job 8aAT-3M-s400 --work /w/g8a --out /w/res/8aAT-3M-s400 --arms AT --accum AT=32 --b2-extra '{\"eg_embed\": true}'" > $T/cmd.txt
python3 -I $T/atcmd.py $T/cmd.txt $T/out.sh /code /o/at_g2 8 300 '--log-every 20'; cat $T/out.sh
echo "AT=16 line:"; sed -i 's/AT=32/AT=16/' $T/cmd.txt; python3 -I $T/atcmd.py $T/cmd.txt $T/out2.sh /code /o 8 300 '--log-every 20' 2>&1 | tail -n 1
echo "--- at_report: synthetic AT log (steps 20..120, log-every 20; elapsed with a slow start), RESULT.json missing = a timeout"
mkdir -p $T/ao/AT
python3 - $T <<'PY'
import json, sys
t = sys.argv[1]
el = {20: 400.0, 40: 520.0, 60: 640.0, 80: 770.0, 100: 890.0, 120: 1010.0}
with open(t + '/ao/AT/stdout.txt', 'w') as f:
    f.write('{"event": "start"}\n')
    for s, e in el.items():
        f.write(json.dumps(dict(event='train', step=s, loss=3.0 - s / 100, lr=0.001, elapsed=e, cap_hits=0)) + '\n')
open(t + '/ao/gpu_used_mib.txt', 'w').write('900\n8123\n9456\n')
json.dump({'sections': {'accumsweep': {'points': {'32': {'s_per_update_median': 5.0}}}}}, open(t + '/sw.json', 'w'))
PY
echo "log" > $T/job.log
python3 -I $T/at_report.py $T/ao at_g1 32 40 300 124 TIMEOUT $T/job.log $T/at_g1.json $T/sw.json; echo "exit $? (0 = a speed number)"
echo "median of intervals 40-60 6.0, 60-80 6.5, 80-100 6.0, 100-120 6.0 -> expect 6.0; json keys:"; python3 -c "import json; d=json.load(open('$T/at_g1.json')); print({k: d[k] for k in ('median_s_per_update','n_intervals','last_step','peak_alloc_gb','gpu_used_max_mib_nvidia_smi','ratio_at_over_b3g2_same_accum')})"
echo "--- at_report: RESULT.json present (finished) with peak 4096 MiB"
echo '{"peak_mem_mib": 4096.0, "peak_reserved_mib": 5000.0, "n_params": 4023302, "train_s": 900}' > $T/ao/AT/RESULT.json
python3 -I $T/at_report.py $T/ao at_g2 16 40 300 143 "training finished, job stopped by the box before its final evaluation" $T/job.log $T/at_g2.json $T/sw.json | tail -n 5; echo "exit $?"
echo "--- at_report: no train lines, an OOM in the job log -> exit 1 and a clear line"
mkdir -p $T/ao2/AT; echo "RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB" > $T/job2.log
python3 -I $T/at_report.py $T/ao2 at_g2 8 40 300 1 ended $T/job2.log $T/at_g2b.json $T/sw.json; echo "exit $? (1 = no speed)"
echo "--- at_report: one log line only after step 40 (not enough for a difference) -> exit 1"
mkdir -p $T/ao3/AT; printf '{"event": "train", "step": 20, "loss": 3.0, "lr": 0.001, "elapsed": 100.0, "cap_hits": 0}\n{"event": "train", "step": 40, "loss": 2.9, "lr": 0.001, "elapsed": 200.0, "cap_hits": 0}\n' > $T/ao3/AT/stdout.txt
python3 -I $T/at_report.py $T/ao3 at_g1 32 40 300 124 TIMEOUT $T/job.log $T/at_g1c.json $T/sw.json | tail -n 4; echo "exit ${PIPESTATUS[0]}"
