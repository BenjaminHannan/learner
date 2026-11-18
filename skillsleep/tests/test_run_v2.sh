#!/usr/bin/env bash
# Control-flow test of run_v2.sh with stubs (no GPU, no network, no models): stage order, which GPU each process gets, the trainer/eval hand-off,
# kill_vllm, resume from done-markers, and that nothing hangs on a bare wait. Usage: bash skillsleep/tests/test_run_v2.sh [TMPDIR]
set -eu
REPO=$(cd "$(dirname "$0")/../.." && pwd); F=${1:-$(mktemp -d)}; rm -rf $F; mkdir -p $F/src/skillsleep/templates $F/bin $F/work/venv/bin $F/work/t2venv/bin $F/work/tau2/data/simulations $F/out $F/base
cp $REPO/skillsleep/common.py $REPO/skillsleep/analyze.py $REPO/skillsleep/t2.sh $REPO/skillsleep/retry_one.sh $REPO/skillsleep/run_v2.sh $F/src/skillsleep/; cp -r $REPO/skillsleep/retry $F/src/skillsleep/
cd $F/src/skillsleep; touch templates/k2_nothink.jinja tau2-judge-haiku.patch; echo '{}' > $F/base/config.json
stub() { printf '%s\n' "$2" > $F/src/skillsleep/$1; }
stub patch_hint.py 'print("ok")'
stub render.py 'print("RENDER SELFTEST OK")'
stub dump_env.py 'import sys; open(sys.argv[1] + "/env_retail.json", "w").write("{}")'
stub anchors.py 'import sys; open(sys.argv[2], "w").write("{}\n"); print("anchors written")'
stub smoke.py 'print("{}")'
stub fix.py 'import json, sys; json.dump({"1": "h"}, open(sys.argv[3], "w"))'
stub build.py 'import sys; open(sys.argv[3] + "/night.jsonl", "w").write("{}\n")'
stub forks.py 'import sys, time; time.sleep(1)
if sys.argv[1] == "make": open(sys.argv[4], "w").write("x")
else: open(sys.argv[6], "w").write("{}\n")'
stub forks_run.py 'import sys, time; time.sleep(1); open(sys.argv[4], "a").write("{}\n"); print("fork sims done")'
stub arc.py 'import json, os, sys; print(json.dumps({"arm": sys.argv[2], "domain": "arc_easy", "sims": 2, "pass": 1, "per_task": {"0": [1], "1": [0]}})); open(os.environ["TRACE"], "a").write("arc %s gpu=%s\n" % (sys.argv[2], os.environ.get("CUDA_VISIBLE_DEVICES")))'
stub train.py 'import json, os, sys, time
arm, outd = sys.argv[1], sys.argv[5]; os.makedirs(outd, exist_ok=True)
open(os.environ["TRACE"], "a").write("train %s seed=%s gpu=%s forks=%s\n" % (arm, os.environ.get("SEED"), os.environ.get("CUDA_VISIBLE_DEVICES"), os.path.exists(os.environ["FORKS"])))
open(outd + ".log", "a").write("step 1\n"); time.sleep(3)
open(outd + "/config.json", "w").write("{}"); open(outd + "/model.safetensors", "w").write("w")
json.dump({"arm": arm, "opt_steps": 10, "dpo_sat_step": None}, open(outd + "/train_info.json", "w")); open(outd + ".log", "a").write("TRAIN DONE %s\n" % arm)'
cat > t2.sh.new << 'EOS'
#!/usr/bin/env bash
name=$1; sleep 1; mkdir -p $T2DIR/data/simulations/$name
python3 -c "import json,sys; json.dump({'simulations':[{'id':'a','task_id':'1','termination_reason':'user_stop','reward_info':{'reward':1},'messages':[]},{'id':'b','task_id':'2','termination_reason':'user_stop','reward_info':{'reward':0},'messages':[]}]}, open('$T2DIR/data/simulations/$name/results.json','w'))"
echo "t2 $name gpu_server=$(cat $(dirname $0)/../../gpu0_server 2>/dev/null)" >> $TRACE
EOS
mv t2.sh.new t2.sh; chmod +x t2.sh
cat > retry_one.sh << 'EOS'
mkdir -p $T2DIR/data/simulations/ss_fix_$1; echo '{"simulations":[]}' > $T2DIR/data/simulations/ss_fix_$1/results.json
EOS
# fake tools on PATH
cat > $F/bin/nvidia-smi << EOS
#!/usr/bin/env bash
case "\$*" in *memory.used*) cat $F/gpu0_used 2>/dev/null || echo 0;; *compute-apps*) ;; *) echo "0, FakeGPU, 24564 MiB";; esac
EOS
for t in git uv; do printf '#!/usr/bin/env bash\ncase "$1 $2" in "clone "*) mkdir -p "${@: -1}";; "venv -q"*) d="${@: -1}"; mkdir -p $d/bin; ln -sf %s/work/venv/bin/python $d/bin/python;; "sync -q") touch $T2VENV/bin/tau2;; esac; exit 0\n' $F > $F/bin/$t; done
cat > $F/work/venv/bin/python << EOS
#!/usr/bin/env bash
case "\$*" in *snapshot_download*) echo $F/base;; *"import vllm"*) echo "vllm fake";; *SKILLSLEEP_HINT*) echo "hint patch active";; *) exec python3 "\$@";; esac
EOS
cat > $F/work/venv/bin/vllm << EOS
#!/usr/bin/env python3
import http.server, os, signal, sys
open("$F/gpu0_used", "w").write("20000"); open("$F/gpu0_server", "w").write(sys.argv[2] + " gpu=" + os.environ.get("CUDA_VISIBLE_DEVICES", ""))
open(os.environ["TRACE"], "a").write("serve %s gpu=%s pgid_is_pid=%s\n" % (sys.argv[2], os.environ.get("CUDA_VISIBLE_DEVICES"), os.getpgrp() == os.getpid()))
def bye(*a): open("$F/gpu0_used", "w").write("0"); open("$F/gpu0_server", "w").write(""); os._exit(0)
signal.signal(signal.SIGTERM, bye)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", 8000), H).serve_forever()
EOS
chmod +x $F/bin/* $F/work/venv/bin/*; ln -sf $F/work/venv/bin/python $F/work/t2venv/bin/python; echo 0 > $F/gpu0_used
export PATH=$F/bin:$PATH TRACE=$F/trace.txt GPUQ_SRC=$F/src GPUQ_OUT=$F/out WORK=$F/work GPUQ_NAME=t CUDA_VISIBLE_DEVICES=2,3 ANTHROPIC_API_KEY=x ORDER="C2s1 C1s1 C3s1" EPOCHS=1
: > $TRACE
timeout 300 bash $REPO/skillsleep/tests/../run_v2.sh > $F/run1.log 2>&1 || { tail -30 $F/run1.log; echo FAIL1; exit 1; }
bash -n $F/src/skillsleep/run_v2.sh
echo "--- trace"; cat $TRACE; echo "--- stages"; grep "=== STAGE" $F/run1.log | grep -v start | tr '\n' ' '; echo
grep -q "STAGE eval_C3s1 rc=0" $F/run1.log || { tail -40 $F/run1.log; echo FAIL: C3s1 not evaluated; exit 1; }
grep -q "train C2s1 seed=1 gpu=3 forks=True" $TRACE && grep -q "train C3s1 seed=1 gpu=3" $TRACE   # training on GPU1 only (the second card)
! grep -E "serve .* gpu=3|arc .* gpu=3" $TRACE   # vLLM and ARC only on the first card
[ "$(grep -c '^serve' $TRACE)" -ge 4 ]   # base, C2s1, C1s1, C3s1
[ ! -e $F/work/merged_C2s1/model.safetensors ] && [ -e $F/work/merged_C2s1/config.json ]   # weights deleted after the eval
python3 - << PY
import json
rows = [json.loads(l) for l in open("$F/out/summary.jsonl")]
print(sorted({(r["arm"], r["domain"]) for r in rows}))
assert {"A0", "C2s1", "C1s1", "C3s1"} <= {r["arm"] for r in rows}
PY
[ -s $F/out/report.md ] && ls $F/out/train_info_C3s1.json > /dev/null
# the A0 eval ran while C2s1 was training: the trainer started before the A0 t2 call
python3 - << PY
t = open("$F/run1.log").read().split("\n")
i = next(i for i, l in enumerate(t) if "[gpu1] training C2s1" in l); j = next(i for i, l in enumerate(t) if "STAGE evalA0 start" in l); assert i < j, (i, j)
PY
echo "--- resume: everything done, must finish fast and run nothing"
: > $TRACE; GPUQ_ATTEMPT=2 timeout 120 bash $REPO/skillsleep/run_v2.sh > $F/run2.log 2>&1 || { tail -20 $F/run2.log; echo FAIL2; exit 1; }
[ ! -s $TRACE ] || { cat $TRACE; echo "FAIL: resume reran work"; exit 1; }
echo "--- resume after losing the trained C1s1 weights before its eval"
rm $F/out/.done/eval_C1s1 $F/out/.done/train_C1s1 $F/out/.done/report; : > $TRACE
GPUQ_ATTEMPT=3 timeout 200 bash $REPO/skillsleep/run_v2.sh > $F/run3.log 2>&1 || { tail -20 $F/run3.log; echo FAIL3; exit 1; }
grep -q "train C1s1" $TRACE && grep -q "serve C1s1" $TRACE && ! grep -q "train C2s1" $TRACE
echo "RUN_V2 CONTROL FLOW OK"
