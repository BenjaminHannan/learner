BASH-ONLY: yes
GPU: rent
THIS JOB is rent-rv390b-p2.md (thought-memory thread, "Memory for its own thoughts", Claude; written 2026-09-27 13:30 UTC by date -u, after the Thread manager's 13:27 review of e49a455c5). Script only, no builder: it rents one vast GPU, runs the sealed re-run step(s) B on rsn-358i2's four loop nets, copies the results back, and destroys the rental.
HELD: this file stays in handoff/held/ until the Director releases it. Ben's yes is his 12:49:44 UTC message (up to $5 total on vast for jobs waiting on BensPC; Director ledger line 2692). Order (Thread manager 13:27 UTC): rsn-358u first, then p1 (steps A, C, D), then this p2 only if what is left of the $5 covers its $1.50; otherwise it waits for BensPC 174. One job at a time. On release it moves to handoff/queue/ unchanged.
BUDGET: $1.50 for this job, failed hosts included. The script keeps it lower: one instance at a time, offers at most $0.90/h, and the watcher's 75-minute alarm ends the job, so at most about $1.13 (4500 s x $0.90/h). Label: claude-thought-rv390b-p2. It stops or destroys only the instance its own create returned (by id), never any other.
END OF A RENTAL: each finished step is copied into a temporary folder on the Mac, checked file by file against a sha256 manifest made on the rental, and only then moved into place with SOURCES.txt. If a copy fails that check twice, nothing is moved into place and the instance is STOPPED, not destroyed, so the results stay on its disk; the reply says so and the thought-memory thread collects them. Otherwise the instance is destroyed at every exit, including the alarm (an unfinished step is never counted). Each end prints a LEDGER line. If the reply has neither "instance ... gone" nor "STOPPING", the Director must check for a live instance with this label.
WHAT IT RUNS: code from git archive of commit f5213af7c (pinned), sealed and unchanged (inference only; no training, no model downloads). A = rv-390 rerun (scripts/claude_rv390.py all, plus the untrained control r0; artifacts/claude-rv390-20260926/ADDENDUM-358i2-rerun.md), B = rv-392 (scripts/claude_rv392.py all, plus r0; PASSMARKS.md and ADDENDUM-1), C = rv-391 practice measure (scripts/claude_rv391_dev.py measure), D = rv-392 daydump (scripts/claude_rv392_daydump.py). The only install is torch 2.11.0 (cu128 wheels) with pip on the rental (the image has 2.8); if 2.11 does not install after 2 tries, the job stops and destroys the rental before running anything (fail closed: torch 2.8's autocast bug). The Mac is unchanged. Nets are read on the Mac in place, checked by sha256 against artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt on both ends, uploaded to the rental only and never pushed; r0 is made on the rental and never pushed. Tested against a fake vast (bad host dropped, deadline kill, duplicate label, alarm, one bad copy retried, two bad copies stop the instance, torch install failure), not yet against the real one.
BENSPC: jobs 173 and 174 run the same four steps for $0. Each job skips a step whose SOURCES.txt is already on main or builder-outbox, and never copies over an output folder that already exists in the worktree. If BensPC comes back before release, this job is withdrawn.
```bash
N=rent-rv390b-p2; LABEL=claude-thought-rv390b-p2; STEPS="B"; TEST=0; CODE=f5213af7c75577b494a22cc8ea05715258db770f; IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime; NETROOTS="$HOME/premonition-models/rsn358i2 $HOME/premonition-models/rsn358i2/W"
set -u; export LC_ALL=C COPYFILE_DISABLE=1
T0=$(date +%s); CAP=4500; MARGIN=540; TMPD=$(mktemp -d); MAXDPH=0.90; PS=15; [ $TEST = 1 ] && PS=1
say() { echo "$(date -u +%H:%M:%S) $*"; }
left() { echo $(( CAP - MARGIN - ($(date +%s) - T0) )); }
out_of() { case $1 in A) echo artifacts/claude-rv390-20260926/run-358i2;; B) echo artifacts/claude-rv392-20260926/run;; C) echo artifacts/claude-rv391-20260926/dev-358i2;; D) echo artifacts/claude-rv392-20260926/daydump;; *) echo probe/$1;; esac; }
have() { [ -e "$1/SOURCES.txt" ] || git cat-file -e "origin/main:$1/SOURCES.txt" 2>/dev/null || git cat-file -e "origin/builder-outbox:$1/SOURCES.txt" 2>/dev/null; }
# Mac python: plain python3 under this bash is a broken x86 binary (000-bash-vastcredit-1250 err.txt), so use uv's 3.12 as the k1h bash jobs do
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=$("$U" python find 3.12 2>/dev/null); [ -x "$PYM" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
[ -x "$PYM" ] || { echo "STOP: no python 3.12 from uv on the Mac; rented nothing"; exit 0; }
command -v vastai >/dev/null || { echo "STOP: vastai CLI missing; rented nothing"; exit 0; }
git cat-file -e "$CODE^{commit}" 2>/dev/null || git fetch -q origin main 2>/dev/null; git cat-file -e "$CODE^{commit}" 2>/dev/null || { echo "STOP: code commit $CODE not found; rented nothing"; exit 0; }
KEY=~/.ssh/id_ed25519
SO="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=8 -o BatchMode=yes"
ID=""; DPH=0; GPU=""; TUP=0; HOST=""; PORT=""; KEEP=0
rx() { ssh $SO -n -p "$PORT" "root@$HOST" "$@"; }   # remote command, no stdin
ri() { ssh $SO -p "$PORT" "root@$HOST" "$@"; }      # remote command, stdin passed
# vastai reads its own key file; this job never reads, prints or passes the key
listed() { vastai show instances --raw 2>/dev/null | "$PYM" -c 'import json,sys; d=json.load(sys.stdin); print(" ".join("%s:%s" % (i.get("id"), i.get("label")) for i in d))' 2>/dev/null; }
inst() { vastai show instances --raw 2>/dev/null | "$PYM" -c 'import json,sys; d=[i for i in json.load(sys.stdin) if str(i.get("id"))==sys.argv[1]]; i=d[0] if d else {}; print(i.get("actual_status"), i.get("ssh_host"), i.get("ssh_port"))' "$1" 2>/dev/null; }
destroy() {
  [ -z "$ID" ] && return 0
  say "destroying instance $ID (this job created it)"; echo y | vastai destroy instance $ID >/dev/null 2>&1; sleep 10
  case " $(listed) " in *" $ID:"*) say "instance $ID still listed; destroying again"; echo y | vastai destroy instance $ID >/dev/null 2>&1; sleep 15
    case " $(listed) " in *" $ID:"*) say "WARNING: instance $ID STILL LISTED after two destroys; the Director must destroy it (label $LABEL)";; *) say "instance $ID gone";; esac;;
  *) say "instance $ID gone";; esac
  m=$(( ($(date +%s) - TUP + 59) / 60 )); c=$(awk -v d="$DPH" -v m="$m" 'BEGIN{printf "%.2f", d*m/60}')
  echo "LEDGER: $(date -u '+%F %T') UTC Memory for its own thoughts: $N, vast instance $ID ($GPU at \$$DPH/h) for $m min = about \$$c (dph x minutes since create; the Director's ledger is the record)"
  ID=""
}
stopinst() {
  [ -z "$ID" ] && return 0
  say "STOPPING (not destroying) instance $ID: a copy-back failed its check, so the results stay on its disk in /root/work"; vastai stop instance $ID >/dev/null 2>&1; sleep 10; say "instance $ID status after stop: $(inst $ID | cut -d' ' -f1)"
  m=$(( ($(date +%s) - TUP + 59) / 60 )); c=$(awk -v d="$DPH" -v m="$m" 'BEGIN{printf "%.2f", d*m/60}')
  echo "LEDGER: $(date -u '+%F %T') UTC Memory for its own thoughts: $N, vast instance $ID ($GPU at \$$DPH/h) ran $m min = about \$$c, then STOPPED, not destroyed (label $LABEL; its disk still costs a little per hour until the thought-memory thread collects the results and the instance is destroyed)"
  ID=""
}
finish() { if [ "$KEEP" = 1 ]; then stopinst; else destroy; fi; }
trap finish EXIT
trap 'say "signal: stopping"; exit 3' ALRM TERM INT HUP
git fetch -q origin builder-outbox 2>/dev/null
say "start $N (BASH-ONLY rental, no builder); code $CODE; steps: $STEPS; test mode: $TEST"
# 0. DUPLICATE per step; no live instance with this label; credit readable
TODO=""; for st in $STEPS; do if have "$(out_of $st)"; then say "step $st: DUPLICATE ($(out_of $st) already delivered): skipped"; else TODO="$TODO $st"; fi; done
[ -z "$TODO" ] && { echo "DUPLICATE: every step was already delivered; rented nothing"; exit 0; }
case " $(listed) " in *":$LABEL "*) echo "DUPLICATE: a live instance is labelled $LABEL; rented nothing, touched nothing"; exit 0;; esac
CR=$(vastai show user --raw 2>/dev/null | "$PYM" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("credit"), d.get("balance"))' 2>/dev/null)
say "vast credit, balance: ${CR:-unreadable}"
case "$CR" in [0-9]*) ;; *) echo "STOP: vast account unreadable; rented nothing"; exit 0;; esac
# 1. nets on the Mac, checked against NETS-358i2 before renting (read in place; only uploaded to the rental, never pushed)
NROOT=""; for r in $NETROOTS; do [ -f "$r/loop-s1/final.pt" ] && { NROOT=$r; break; }; done
[ -n "$NROOT" ] || { echo "STOP: rsn358i2 nets not found on the Mac; rented nothing"; exit 0; }
SEEDS=""; for s in 1 2 3 4; do
  want=$(git show $CODE:artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt | awk -v k="loop-s$s/final.pt" '$2==k{print $1}')
  got=$(shasum -a 256 "$NROOT/loop-s$s/final.pt" 2>/dev/null | cut -d' ' -f1)
  if [ -n "$want" ] && [ "$want" = "$got" ]; then SEEDS="$SEEDS $s"; eval "SHA_$s=$got"; else say "net s$s: missing or no match on the Mac (want $want, got $got): skipped"; fi
done
[ $(echo $SEEDS | wc -w) -ge 3 ] || { echo "STOP: fewer than 3 nets match NETS-358i2 on the Mac; rented nothing"; exit 0; }
say "Mac nets ($NROOT): seeds$SEEDS match"
# 2. job scripts (run on the rental from files)
mkdir -p "$TMPD/job"
cat > "$TMPD/job/setup.sh" <<'EOS'
cd /root/work || { echo NO-FOLDER; exit 9; }
for f in artifacts/claude-rv390-20260926/SEAL.sha256.txt artifacts/claude-rv392-20260926/SEAL.sha256.txt artifacts/claude-rv392-20260926/SEAL-addendum-1.sha256.txt; do
  echo "seal $f $(sha256sum -c "$f" 2>&1 | grep -c ': OK$') $(grep -c . "$f")"; sha256sum -c "$f" 2>&1 | grep -v ': OK$' | sed 's/^/sealfail /'
done
python -B scripts/claude_rv392_randnet.py --out /root/work/RAND/loop-r0.pt --seed 0 2>&1 | tail -3 | sed 's/^/r0print /'
[ -f RAND/loop-r0.pt ] && echo "r0file ok"
python -c "import torch;print('torch', torch.__version__, torch.version.cuda)" 2>&1 | tail -1
echo "gpu $(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | head -1)"
EOS
cat > "$TMPD/job/step.sh" <<'EOS'
cd /root/work || exit 9
STEP=$1; BUDGET=$2; HAVE_R0=$3; shift 3; SEEDS="$*"
case $STEP in
  A) O=artifacts/claude-rv390-20260926/run-358i2; X="scripts/claude_rv390.py all"; R=1;;
  B) O=artifacts/claude-rv392-20260926/run; X="scripts/claude_rv392.py all"; R=1;;
  C) O=artifacts/claude-rv391-20260926/dev-358i2; X="scripts/claude_rv391_dev.py measure"; R=0;;
  D) O=artifacts/claude-rv392-20260926/daydump; X="scripts/claude_rv392_daydump.py"; R=0;;
  T1|T2) O=probe/$STEP; X="job/sleeper.py $STEP"; R=1;;
  *) echo "unknown step $STEP"; exit 8;;
esac
mkdir -p $O; L=""; for s in $SEEDS; do L="$L s$s"; done; [ $R = 1 ] && [ "$HAVE_R0" = 1 ] && L="$L r0"
pids=""; names=""
for k in $L; do
  if [ $k = r0 ]; then CK=RAND/loop-r0.pt; else CK=NETS/loop-$k/final.pt; fi
  case $STEP in A) OUT=$O/rv390-$k;; B) OUT=$O/rv392-$k;; C) OUT=$O/measure-$k.json;; D) OUT=$O/day-$k.jsonl;; *) OUT=$O/out-$k.txt;; esac
  python -B $X --ckpt $CK --out $OUT > $O/log-$k.txt 2>&1 &
  pids="$pids $!"; names="$names $k"
done
echo "$pids" > job/pids-$STEP.txt; echo "started:$names | pids:$pids"
end=$(( $(date +%s) + BUDGET )); killed=0
while :; do
  alive=0; for p in $pids; do kill -0 $p 2>/dev/null && alive=$((alive+1)); done
  [ $alive = 0 ] && break
  if [ $(date +%s) -ge $end ]; then echo "DEADLINE: $alive runs still going; stopping this step's own runs by exact PID"; kill $pids 2>/dev/null; sleep 5; kill -9 $pids 2>/dev/null; killed=1; break; fi
  sleep 10
done
set -- $names
for p in $pids; do wait $p; echo "$1 rc=$? last: $(tail -1 $O/log-$1.txt 2>/dev/null | cut -c1-600)"; shift; done
echo "STEP-END $STEP killed=$killed"
EOS
if [ $TEST = 1 ]; then cat > "$TMPD/job/sleeper.py" <<'EOS'
import sys, time
step = sys.argv[1]; out = sys.argv[sys.argv.index("--out") + 1]; ck = sys.argv[sys.argv.index("--ckpt") + 1]
t = 3 if (step == "T1" or ck.endswith("loop-s1/final.pt")) else 400
time.sleep(t); open(out, "w").write("slept %d\n" % t); print("sleeper", step, "slept", t)
EOS
fi
# 3. rent: cheapest RTX 5090 or 4090 at most $MAXDPH/h, reliability >= 0.98, at least 8 cores; at most 3 hosts (rent-rv390 on 09-26 needed 3: one could not pull the image, one stuck loading)
for g in RTX_5090 RTX_4090; do vastai search offers "gpu_name=$g num_gpus=1 reliability>=0.98 cpu_cores>=8 disk_space>=30 inet_down>=200 rentable=true" -o dph --raw > "$TMPD/off-$g.json" 2>/dev/null; done
"$PYM" - "$TMPD" "$MAXDPH" > "$TMPD/offers.txt" <<'EOS'
import json, sys, glob
offs = []
for f in glob.glob(sys.argv[1] + "/off-*.json"):
    try: offs += json.load(open(f))
    except Exception: pass
offs = [o for o in offs if o.get("dph_total") and o["dph_total"] <= float(sys.argv[2])]
for o in sorted(offs, key=lambda o: o["dph_total"])[:4]:
    print(o["id"], round(o["dph_total"], 4), str(o.get("gpu_name", "?")).replace(" ", "_"))
EOS
say "offers (id, \$/h, gpu):"; cat "$TMPD/offers.txt"
for try in 1 2 3; do
  line=$(sed -n "${try}p" "$TMPD/offers.txt"); [ -z "$line" ] && break
  set -- $line; OFFER=$1; DPH=$2; GPU=$3
  ID=$(vastai create instance $OFFER --image $IMAGE --disk 30 --label $LABEL --ssh --direct --raw 2>&1 | grep -o 'new_contract[^0-9]*[0-9][0-9]*' | grep -o '[0-9][0-9]*$' | head -1)
  [ -n "$ID" ] || { say "create failed on offer $OFFER"; continue; }
  TUP=$(date +%s); say "created instance $ID on offer $OFFER ($GPU, \$$DPH/h), label $LABEL"
  ok=0; att=0; st=none
  for i in $(seq 1 32); do
    set -- $(inst $ID) x x x; st=$1; HOST=$2; PORT=$3
    if [ "$st" = running ] && [ "$HOST" != None ] && [ "$HOST" != x ]; then
      [ $(( att % 8 )) = 0 ] && vastai attach ssh $ID "$(cat $KEY.pub)" >/dev/null 2>&1; att=$((att+1))
      rx 'echo SSH_OK' 2>/dev/null | grep -q SSH_OK && { ok=1; break; }
    fi
    sleep $PS
  done
  [ $ok = 1 ] && break
  say "instance $ID not reachable in 8 min (last status $st): destroying, next offer"; destroy
done
[ -n "$ID" ] || { echo "STOP: no reachable rental after 3 tries"; exit 0; }
say "ssh ok: instance $ID"
# 4. torch 2.11 with CUDA (inference only; the image has 2.8)
TV=$(rx 'python -c "import torch;print(torch.__version__)"' 2>&1 | tail -1); say "image torch: $TV"
for t in 1 2; do case "$TV" in 2.11.*) break;; esac
  say "installing torch 2.11.0 (cu128 wheels), in the foreground (try $t)"; rx 'timeout 600 pip install -q torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > /root/pip.log 2>&1; echo pip-rc=$?; tail -2 /root/pip.log' 2>&1 | tail -3
  TV=$(rx 'python -c "import torch;print(torch.__version__)"' 2>&1 | tail -1); done
CT=$(rx 'python -c "import torch; a=torch.randn(256,256,device=\"cuda\"); print(\"torchok\", torch.__version__, torch.version.cuda, bool((a@a).isfinite().all()))"' 2>&1 | tail -1); say "$CT"
case "$CT" in torchok*True) ;; *) echo "STOP: torch with CUDA does not work on the rental"; exit 0;; esac
case "$CT" in "torchok 2.11."*) ;; *) echo "STOP: torch 2.11 did not install (rental has $(echo "$CT" | awk '{print $2}')); fail closed (the torch 2.8 autocast bug), ran nothing"; exit 0;; esac
# 5. code tree, nets (each checked on the rental; a net that arrives changed is sent once more), job scripts
git archive $CODE scripts artifacts/claude-rv390-20260926 artifacts/claude-rv392-20260926 artifacts/claude-rv391-20260926 | ri 'mkdir -p /root/work && tar -x -C /root/work'; say "code tree sent (rc $?)"
S2=""; for s in $SEEDS; do
  eval "w=\$SHA_$s"
  for t in 1 2; do
    tar -cf - -C "$NROOT" loop-s$s/final.pt | ri 'mkdir -p /root/work/NETS && tar -x -C /root/work/NETS'
    g=$(rx "sha256sum /root/work/NETS/loop-s$s/final.pt" 2>/dev/null | cut -d' ' -f1)
    [ "$g" = "$w" ] && { S2="$S2 $s"; break; }
    say "net s$s arrived changed (send $t): $g"
  done
done; SEEDS=$S2
[ $(echo $SEEDS | wc -w) -ge 3 ] || { echo "STOP: fewer than 3 nets arrived intact; ran nothing"; exit 0; }
say "nets on the rental match NETS-358i2: seeds$SEEDS"
tar -cf - -C "$TMPD" job | ri 'tar -x -C /root/work'; say "job scripts sent (rc $?)"
# 6. seals, untrained control r0
CHK=$(rx 'bash /root/work/job/setup.sh' 2>&1); echo "$CHK"
SOK=1
for want in "artifacts/claude-rv390-20260926/SEAL.sha256.txt 15" "artifacts/claude-rv392-20260926/SEAL.sha256.txt 14" "artifacts/claude-rv392-20260926/SEAL-addendum-1.sha256.txt 2"; do
  f=${want% *}; n=${want##* }; got=$(echo "$CHK" | awk -v f="$f" '$1=="seal" && $2==f {print $3" "$4}')
  [ "$got" = "$n $n" ] || { SOK=0; say "seal $f: '$got' (want $n of $n)"; }
done
[ $SOK = 1 ] || { echo "STOP: a seal line did not match; ran nothing"; exit 0; }
R0LINE=$(echo "$CHK" | sed -n 's/^r0print //p' | grep weights_sha256 | tail -1); HAVE_R0=0
echo "$CHK" | grep -q '^r0file ok' && [ -n "$R0LINE" ] && HAVE_R0=1
TORCHLINE=$(echo "$CHK" | grep '^torch ' | tail -1); GPUNAME=$(echo "$CHK" | sed -n 's/^gpu //p')
say "seeds:$SEEDS; r0 made: $HAVE_R0"
# 7. steps in order; each runs detached on the rental with its own budget; results copied back only if the step ended in time
DONE=""; NOTRUN=""
for st in $TODO; do
  b=$(left); if [ $TEST = 1 ]; then [ $st = T1 ] && b=60; [ $st = T2 ] && b=30; fi
  if [ $TEST = 0 ] && [ $b -lt 600 ]; then say "step $st: not started (only $b s left in this job)"; NOTRUN="$NOTRUN $st"; continue; fi
  say "step $st: start, budget $b s"; t1=$(date +%s)
  rx "cd /root/work && setsid nohup bash job/step.sh $st $b $HAVE_R0 $SEEDS > job/out-$st.txt 2>&1 < /dev/null & echo launched" 2>&1 | tail -1
  hard=$(( t1 + b + 180 )); ended=0
  while [ $(date +%s) -lt $hard ]; do sleep 20; c=$(rx "grep -c '^STEP-END' /root/work/job/out-$st.txt" 2>/dev/null | tail -1); [ "$c" = 1 ] && { ended=1; break; }; done
  [ $ended = 1 ] || { say "step $st: no STEP-END 3 min past its budget; stopping its runs by exact PID"; rx "kill \$(cat /root/work/job/pids-$st.txt) 2>/dev/null; sleep 5; kill -9 \$(cat /root/work/job/pids-$st.txt) 2>/dev/null; true"; }
  rx "cat /root/work/job/out-$st.txt" 2>&1; m=$(( ($(date +%s) - t1 + 30) / 60 )); say "step $st: about $m min"
  if rx "grep -q '^STEP-END $st killed=0' /root/work/job/out-$st.txt"; then
    o=$(out_of $st); DEST=.; [ $TEST = 1 ] && { DEST="$TMPD/copy"; mkdir -p "$DEST"; }
    [ -e "$DEST/$o" ] && { say "step $st: $o already exists here (another job wrote it): this step's output is not copied"; NOTRUN="$NOTRUN $st"; continue; }
    cok=0; for t in 1 2; do
      rx "cd /root/work && find $o -type f | LC_ALL=C sort | xargs sha256sum" > "$TMPD/man-$st.txt" 2>/dev/null; nm=$(grep -c . "$TMPD/man-$st.txt" 2>/dev/null); nm=${nm:-0}
      rm -rf "$TMPD/in-$st"; mkdir -p "$TMPD/in-$st"
      rx "tar -cf - -C /root/work $o" | tar -x -C "$TMPD/in-$st"
      nf=$(find "$TMPD/in-$st/$o" -type f 2>/dev/null | wc -l | tr -d ' ')
      nok=$(cd "$TMPD/in-$st" && shasum -a 256 -c "$TMPD/man-$st.txt" 2>/dev/null | grep -c ': OK$')
      say "step $st: copy $t: $nf files here, manifest $nm, sha256 OK $nok"
      [ "$nm" -gt 0 ] && [ "$nf" = "$nm" ] && [ "$nok" = "$nm" ] && { cok=1; break; }
    done
    if [ $cok = 1 ]; then mkdir -p "$(dirname "$DEST/$o")"; mv "$TMPD/in-$st/$o" "$DEST/$o"; DONE="$DONE $st"; {
      echo "$N sources (BASH-ONLY rental job, no builder; step $st; written $(date -u +%FT%TZ))"
      echo "code: git archive $CODE; vast instance $ID, offer GPU $GPU at \$$DPH/h; nvidia-smi: $GPUNAME"; echo "python torch CUDA: $TORCHLINE"
      for s in $SEEDS; do eval "h=\$SHA_$s"; echo "loop-s$s: Mac $NROOT/loop-s$s/final.pt, uploaded to NETS/loop-s$s/final.pt, sha256 $h on both ends (matches NETS-358i2.sha256.txt)"; done
      case $st in A|B|T*) [ $HAVE_R0 = 1 ] && echo "r0 (untrained control, made on the rental, never pushed): $R0LINE";; esac
      echo "minutes for step $st: $m"
      echo "manifest made on the rental after STEP-END killed=0 ($nm files, all sha256 re-checked on the Mac before the folder was moved into place):"; cat "$TMPD/man-$st.txt"; } > "$DEST/$o/SOURCES.txt"
      say "step $st: delivered ($nm files)"
    else KEEP=1; NOTRUN="$NOTRUN $st"; say "step $st: COPY CHECK FAILED twice; nothing moved into place; the instance will be stopped, not destroyed"; fi
  else say "step $st: incomplete (deadline, error or ssh loss); its partial output is not copied"; NOTRUN="$NOTRUN $st"; fi
done
[ $TEST = 1 ] && { echo "--- test copy:"; find "$TMPD/copy" -type f 2>/dev/null | sed "s|$TMPD/||" | sort; cat "$TMPD"/copy/probe/*/SOURCES.txt 2>/dev/null; }
echo "RESULT: delivered steps:${DONE:- none}; not run or incomplete:${NOTRUN:- none}; seeds:$SEEDS; r0 made: $HAVE_R0; instance kept stopped: $KEEP"
finish
rm -rf "$TMPD"
```
PUSH: artifacts/claude-rv390-20260926/run-358i2 artifacts/claude-rv392-20260926/run artifacts/claude-rv391-20260926/dev-358i2 artifacts/claude-rv392-20260926/daydump
