#!/bin/bash
# y1t vast pass, run on the Mac from the watcher's worktree by the BASH-ONLY queue jobs rent-y1t-vast-p1..p3
# (Answering-from-memory thread, 2026-09-27; artifacts/claude-y1t-20260926/ADDENDUM-9-vast.md). The vast version of
# handoff/kit/y1tpc/pass.sh: BensPC has been unreachable since 12:30 UTC 09-27 and Ben said "Just use vast for now".
# Every pass is state-driven, so a later pass picks up where the last one stopped:
#   rent     first pass only: the 1-GPU offer with the best TFLOPS per $/h that fits (Ben, 14:05 UTC), labelled
#            claude-memory-y1t, after re-checking that this job file is still in handoff/queue/ on origin/main; a new
#            instance not running within 6 minutes is destroyed by its exact id and another host is tried; at most 3
#            creates in all
#   tree     ~/tree on the rental is made once from `git archive` of the pinned commit, then marked with the pin
#   setup    torch 2.11.0 (cu128) and transformers 5.17.0 (BensPC's versions); MiniCPM5-1B at commit 87179e5c only
#   checks   seals, items sha256 and the four selftests, once
#   launch   remote/chain.sh starts once, detached, and watches its own steps (stall, step, chain and money caps)
#   watch    until 55 minutes into the pass (45 for the last pass); a pass that is not the last leaves a running chain
#            for the next pass
#   done     copy the results back and check every file's sha256 against the rental's manifest, copy the adapter to
#            the Mac, then destroy the instance and confirm it is gone; write RESULTS-vast.md (no verdict: the thread
#            scores it). The instance is destroyed only after a checked copy: if the check fails twice, a pass that is
#            not the last leaves it running, and the last pass (or a failure stop) STOPS it instead (GPU billing ends,
#            its disk keeps the files) and prints FLAG-DIRECTOR (the Thread manager's rule for vast kits, 13:27 UTC).
# Every exit that leaves an instance of this task running says so: NEXT-PASS-NEEDED from a pass that is not the last
# (the next pass must be released), ACTION NEEDED (FLAG-DIRECTOR) from the last pass. An instance that never answered
# ssh as this task's instance has nothing on it and is destroyed. Every vastai and ssh call has a time limit, and the
# job block execs this script, so the watcher's 75-minute alarm reaches it (the ALRM trap writes the same notes).
# It never edits sealed code, never opens the TEST-ONLY panel or the H1 rows, never pushes weights, never reads or
# prints the vast key (the vastai CLI reads its own key file; only the ssh public key is sent, with `vastai attach ssh`)
# and never touches an instance this task did not create.
# Usage: pass.sh <kit-dir> <pinned-commit> <queue-job-name> <first|next|last> [<the watcher's copy of the job file>]
set -u
export LC_ALL=C COPYFILE_DISABLE=1
KD=$1; PIN=$2; JOB=${3:-?}; MODE=${4:-next}; QF=${5:-}
LAST=""; case "$MODE" in last|guard) LAST=1 ;; esac   # the guard acts like a last pass, at once, and never launches
G=${GY1T:-$HOME/premonition-watch/y1t-vast}         # Mac-only guard state (its own kit copy, pid, log); never pushed
A=artifacts/claude-y1t-20260926
H=artifacts/claude-y1tH1-20260926
R=$A/run
RH=$H/run
D=$A/glm2/items
TRAIN_SHA=47e2e2955bf085816abcda50fdfc4230d0030cbe72b5d8df4109e704858c79e4
DEV_SHA=c0288f2cb7a5b764f974f49d1bfeb5b8ddb0de68e8ce63fffc6cc4d0a3d407e4
MINICPM=87179e5c1f455ef22e6223592d2d61351b525bfc
LABEL=claude-memory-y1t
CAP=${CAPY1T:-1.50}          # dollars for this whole task, every create included (ADDENDUM-9)
MAXDPH=${MAXDPHY1T:-1.00}    # dollars per hour, the most an offer may cost (the time estimate below also has to fit the cap)
REFTF=104.8                  # TFLOPS of an RTX 5090 in vast's listing (the card the estimate below is for; as rent-rv390b)
REFMIN=50                    # chain minutes on an RTX 5090, an upper guess (ADDENDUM-9: drafts, train, 2 DEV checks, 2 H1 runs)
MAXCREATE=3
IMAGE=pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
VAST=${VASTY1T:-vastai}
SSHB=${SSHBINY1T:-ssh}
KEY=${KEYY1T:-$HOME/.ssh/id_ed25519}   # the Mac's ssh key; its .pub is attached to the new instance (as the sleep kit and rent-rv390b do)
SSHO="-i $KEY -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
MA=${MAY1T:-$HOME/y1t-adapter}
WATCH=${WATCHY1T:-3300}; S1=${S1Y1T:-60}; RUNWAIT=${RUNWAITY1T:-360}; POLL=${POLLY1T:-20}; SSHWAIT=${SSHWAITY1T:-240}
[ "${4:-}" = last ] && WATCH=${WATCHLASTY1T:-2700}   # the last pass keeps 30 minutes for the stop, the copy and the destroy
[ "${4:-}" = guard ] && WATCH=0
NETGB=8             # GB each instance downloads (torch cu128 wheels and MiniCPM5-1B; a guess), priced at its $/GB in spent()
MAXNET=0.02         # dollars per GB, the most an offer may charge for download or upload
# Mac python: plain python3 under the watcher's bash is a broken x86 binary (000-bash-vastcredit-1250), so use uv's 3.12
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PYM=${PYMY1T:-$("$U" python find 3.12 2>/dev/null)}
[ -x "$PYM" ] || [ -n "${PYMY1T:-}" ] || PYM=$("$U" run --offline --no-project --python 3.12 python -c 'import sys; print(sys.executable)' 2>/dev/null)
KR=handoff/kit/y1tvast/remote
NOTE=$R/RUN-NOTE-vast.md
VS=$R/vast-state.txt
T0=$(date +%s)
now() { date -u +%FT%TZ; }
note() { echo "- $(now) $JOB: $*" >> "$NOTE"; echo "NOTE: $*"; }
elapsed() { echo $(( $(date +%s) - T0 )); }
sv() { echo "$ST" | awk -v k="$1" '$1==k {sub("^" k " ?",""); print; exit}'; }
hms() { date -u -r "$1" +%FT%TZ 2>/dev/null || date -u -d "@$1" +%FT%TZ; }
# time limits: every vastai and ssh call is ended by SIGALRM after its limit (seconds), so no call can hang a pass
tmo() { local n=$1; shift; perl -e 'alarm shift; exec @ARGV' "$n" "$@"; }
vast() { tmo "${VT:-90}" "$VAST" "$@"; }
sx() { tmo "${SXT:-120}" $SSHB $SSHO -p "$PORT" "root@$HOSTN" "$@"; }
pending() {  # what an exit leaves behind; says nothing when no instance of this task can still be running
  local i; i=$(curid 2>/dev/null); [ -n "$i" ] || return 0
  grep -q "^STOPPED [0-9]* $i\$" "$VS" 2>/dev/null && return 0
  # the copy was checked (COLLECTED) but the destroy was not confirmed: destroy it now
  grep -q "^COLLECTED [0-9]* $i " "$VS" && vdestroy "$i" "results already copied and checked" && return 0
  if [ -n "$LAST" ]; then
    note "ACTION NEEDED (FLAG-DIRECTOR): the last pass ended ($(echo "$1" | cut -c1-80)) and instance $i labelled $LABEL is not confirmed destroyed or stopped; it may still be running and billing"
  else
    note "NEXT-PASS-NEEDED: instance $i keeps running and billing at \$$(dphof "$i")/h until a later pass or the guard copies back and destroys it; \$$(spent) spent so far; the guard (pid $(cat "$G/guard.pid" 2>/dev/null)) acts at the \$$CAP cap (about $(capat "$i") UTC) or the time cap ($(hms "$(tcap "$i")")), whichever comes first"
  fi
}
stop() { note "$*"; pending "$*"; echo "PASS-END $(now)"; exit 0; }
tcap() {  # the time cap of instance $1 (epoch): create + 20 min setup + 2 x the offer's estimated chain minutes + 15 min
  awk -v i="$1" '$1=="CREATE" && $3==i {c=$2} $1=="EST" && $2==i {e=$3} END{if(e=="") e=120; printf "%d", c+(20+2*e+15)*60}' "$VS"; }
ensure_guard() {  # start the Mac-side guard (guard.sh) unless it runs already: between passes it enforces the money cap and
  # the time cap by running this script in guard mode (copy back, then destroy, else stop). It runs from its own copy of
  # the kit in $G, detached (its own session, caffeinate on the Mac), so it outlives this pass and the job's temporary kit.
  local p c
  p=$(cat "$G/guard.pid" 2>/dev/null)
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null && ps -p "$p" -o args= 2>/dev/null | grep -q 'y1tvast/guard\.sh' && return 0
  mkdir -p "$G"; rm -rf "$G/kit"; mkdir -p "$G/kit/handoff/kit"; cp -R "$KD/handoff/kit/y1tvast" "$G/kit/handoff/kit/"
  c=""; command -v caffeinate > /dev/null && c="caffeinate -i"
  nohup perl -e 'use POSIX qw(setsid); setsid(); exec @ARGV' $c bash "$G/kit/handoff/kit/y1tvast/guard.sh" "$G" "$PWD" "$PIN" > "$G/guard.out" 2>&1 < /dev/null &
  echo $! > "$G/guard.pid"
  note "guard started (pid $!; $G/guard.log): at the \$$CAP cap or the time cap ($(hms "$(tcap "$ID")")) it copies back, then destroys, else stops"
}
capat() { hms "$(awk -v t="$(date +%s)" -v c="$CAP" -v s="$(spent)" -v p="$(dphof "$1")" 'BEGIN{if(p<=0)p=1; x=(c-s)/p*3600; if(x<0)x=0; printf "%d", t+x}')"; }

# ---- vast (python only parses the CLI's JSON; the create reply's instance key is never printed)
vlist() {  # every instance with this task's label: id status dph ssh_host ssh_port gpu start; ERR if vast did not answer
  vast show instances --raw < /dev/null 2>/dev/null | "$PYM" -c '
import json, sys
try:
    d = json.load(sys.stdin)
    d = d.get("instances", d) if isinstance(d, dict) else d
except Exception:
    print("ERR"); sys.exit(0)
for i in d:
    if (i.get("label") or "") == sys.argv[1]:
        try:
            sd = int(float(i.get("start_date")))
        except Exception:
            sd = "?"
        print(i.get("id"), i.get("actual_status"), round(float(i.get("dph_total") or 0), 4), i.get("ssh_host"), i.get("ssh_port"),
              str(i.get("gpu_name")).replace(" ", "_"), sd)
' "$LABEL"
}
vlist5() {  # vlist, asked up to 5 times a minute apart when vast does not answer; ERR (status 1) after that
  local k=0 x
  while :; do
    x=$(vlist); [ "$x" != ERR ] && { [ -n "$x" ] && echo "$x"; return 0; }
    k=$((k+1)); [ $k -lt 5 ] || { echo ERR; return 1; }; sleep "${VRSLEEPY1T:-60}"
  done
}
adopt() {  # $1 = vlist lines, $2 = "host machine download-$/GB" of the offer when known. A labelled instance with no CREATE line that started after this task's first create call
  # was made by a create whose reply was lost: write its CREATE line (it has no UP line, so it is destroyed unless this
  # pass's own rent loop sees it answer ssh). Prints the labelled instances that are neither this task's nor adoptable.
  local fc lc i st p h pt g sd
  fc=$(awk '$1=="CALL"{print $2; exit}' "$VS"); lc=$(awk '$1=="CALL"{c=$2; o=$3} END{print c, o}' "$VS")
  echo "$1" | while read -r i st p h pt g sd; do
    [ -n "$i" ] || continue
    grep -q "^CREATE [0-9]* $i " "$VS" && continue
    if [ -n "$fc" ] && { [ "$sd" = "?" ] || [ "$sd" -ge $((fc - 120)) ] 2>/dev/null; }; then
      [ "$sd" = "?" ] && sd=${lc% *}   # no start time from vast: bill it from the last create call (the earliest it can be)
      echo "CREATE $sd $i ${lc#* } $g $p ${2:-? ? ?}" >> "$VS"
      note "ADOPTED instance $i ($g, \$$p/h, '$st', started $(hms "$sd")): it carries this task's label and was made by a create call whose reply was lost" >&2
    else echo "$i($st)"; fi
  done
}
sweep() {  # at the end of a run: adopt instances made by lost create replies, then destroy every listed instance of this
  # task that never answered ssh, other than $1 (nothing is on them). Status 1 when a destroy is not confirmed.
  local L f o rc=0
  L=$(vlist); [ "$L" = ERR ] && { note "sweep: vast did not answer; other instances of this task not checked"; return 0; }
  f=$(adopt "$L"); [ -n "$f" ] && note "vast lists $f labelled $LABEL that this task did not create; not touched"
  for o in $(echo "$L" | awk -v i="${1:-}" 'NF && $1!=i {print $1}'); do
    grep -q "^CREATE [0-9]* $o " "$VS" || continue
    grep -q "^UP [0-9]* $o " "$VS" && continue
    vdestroy "$o" "never came up; left from a create of this task" || {
      note "ACTION NEEDED (FLAG-DIRECTOR): instance $o labelled $LABEL (never came up) is not confirmed destroyed"; rc=1; }
  done
  return $rc
}
vlabel() {  # the label of instance $1, GONE if vast does not list it, ERR if vast did not answer
  vast show instances --raw < /dev/null 2>/dev/null | "$PYM" -c '
import json, sys
try:
    d = json.load(sys.stdin)
    d = d.get("instances", d) if isinstance(d, dict) else d
except Exception:
    print("ERR"); sys.exit(0)
m = [i for i in d if str(i.get("id")) == sys.argv[1]]
f = sys.argv[2]
print((m[0].get(f) or "none") if m else "GONE")
' "$1" "${2:-label}"
}
vstatus() { vlabel "$1" actual_status; }
credit() { vast show user --raw < /dev/null 2>/dev/null | "$PYM" -c 'import json, sys; print(json.load(sys.stdin).get("credit"))' 2>/dev/null; }
spent() {  # dollars so far: dph x hours for every instance this task created, from its create until confirmed gone,
  # plus NETGB x its download $/GB for every instance that answered ssh (GPU billing ends when an instance is stopped or
  # gone; a stopped instance's small storage charge is not counted). An adopted instance's $/GB is taken as MAXNET.
  awk -v t="$(date +%s)" -v g="$NETGB" -v mx="$MAXNET" '$1=="CREATE"{c[$3]=$2; p[$3]=$6; n[$3]=($9=="" || $9=="?")?mx:$9} $1=="DPH"{p[$2]=$3}
    $1=="UP"{u[$3]=1} ($1=="GONE" || $1=="STOPPED") && !($3 in e){e[$3]=$2}
    END{s=0; for(i in c){x=(i in e)?e[i]:t; s+=p[i]*(x-c[i])/3600; if(i in u) s+=g*n[i]}; printf "%.2f\n", s}' "$VS"; }
ncreate() { awk '$1=="CALL"{n++} END{print n+0}' "$VS"; }   # every create call counts, even one that made nothing
curid() {  # this task's instance: the last one created that is not gone, preferring one that answered ssh (UP)
  awk '$1=="CREATE"{o[++n]=$3} $1=="UP"{u[$3]=1} $1=="GONE"{g[$3]=1}
    END{for(k=n;k>=1;k--) if(!(o[k] in g) && (o[k] in u)){print o[k]; exit}; for(k=n;k>=1;k--) if(!(o[k] in g)){print o[k]; exit}}' "$VS"; }
dphof() { awk -v i="$1" '$1=="CREATE" && $3==i {p=$6} $1=="DPH" && $2==i {p=$3} END{print p+0}' "$VS"; }
over() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a+0 >= b+0)}'; }   # true when $1 >= $2
vdestroy() {  # $1 = id, then why. Only an id this task created that still carries this task's label
  local id=$1 lab k; shift
  awk -v i="$id" '$1=="CREATE" && $3==i {f=1} END{exit f?0:1}' "$VS" || { note "REFUSED to destroy $id: this task did not create it"; return 1; }
  lab=$(vlabel "$id")
  case "$lab" in
    GONE) echo "GONE $(date +%s) $id" >> "$VS"; note "instance $id is already gone"; return 0 ;;
    "$LABEL") ;;
    *) note "REFUSED to destroy $id: its label is '$lab'"; return 1 ;;
  esac
  echo "DESTROY $(date +%s) $id $*" >> "$VS"
  echo "destroy $id: $(yes | vast destroy instance "$id" 2>&1 | tail -1 | cut -c1-120)"
  k=0; while [ $k -lt 12 ]; do
    sleep "${DSLEEPY1T:-10}"; k=$((k+1))
    [ "$(vlabel "$id")" = GONE ] && { echo "GONE $(date +%s) $id" >> "$VS"; note "destroyed $id ($*); vast no longer lists it"; return 0; }
  done
  note "DESTROY-UNCONFIRMED: vast still lists $id two minutes after the destroy; the next pass or the thread must destroy it"
  return 1
}
vstop() {  # $1 = id, then why: stop (not destroy) an instance of ours; GPU billing ends, its disk keeps the files
  local id=$1 k st; shift
  awk -v i="$id" '$1=="CREATE" && $3==i {f=1} END{exit f?0:1}' "$VS" || { note "REFUSED to stop $id: this task did not create it"; return 1; }
  [ "$(vlabel "$id")" = "$LABEL" ] || { note "REFUSED to stop $id: its label is '$(vlabel "$id")'"; return 1; }
  echo "STOP $(date +%s) $id $*" >> "$VS"
  echo "stop $id: $(yes | vast stop instance "$id" 2>&1 | tail -1 | cut -c1-120)"
  k=0; while [ $k -lt 12 ]; do
    sleep "${DSLEEPY1T:-10}"; k=$((k+1)); st=$(vstatus "$id")
    case "$st" in exited|stopped|GONE) echo "STOPPED $(date +%s) $id" >> "$VS"; note "stopped $id (status $st), not destroyed: its disk keeps the files (a small storage charge continues)"; return 0 ;; esac
  done
  note "STOP-UNCONFIRMED: $id is '$(vstatus "$id")' two minutes after the stop"
  return 1
}
released() {  # RE-CHECK BEFORE EACH RENTAL (rent kit): this job file is in handoff/queue/ on origin/main, unchanged
  tmo 120 git fetch -q origin main 2>/dev/null || { echo "git fetch failed"; return 1; }
  git cat-file -e "origin/main:handoff/queue/$JOB.md" 2>/dev/null || { echo "handoff/queue/$JOB.md is not on origin/main"; return 1; }
  git cat-file -e "origin/main:handoff/held/$JOB.md" 2>/dev/null && { echo "handoff/held/$JOB.md exists on origin/main"; return 1; }
  git show "origin/main:handoff/queue/$JOB.md" | grep -q '^STATUS: HELD' && { echo "the job file has a STATUS: HELD line"; return 1; }
  # one y1t route only: no BensPC y1t pass may be in the queue while this one rents
  git ls-tree --name-only origin/main handoff/queue/ | grep -q '180-y1t-benspc-bo-p' && { echo "a BensPC y1t pass (180-y1t-benspc-bo-p*) is in handoff/queue/ on origin/main"; return 1; }
  if [ -n "$QF" ] && [ -f "$QF" ]; then
    git show "origin/main:handoff/queue/$JOB.md" | cmp -s - "$QF" || { echo "the job file changed after the watcher launched it"; return 1; }
  fi
  return 0
}
offer() {  # the offer with the best TFLOPS per $/h (Ben's standing order, 14:05 UTC 09-27, via the Director) among 1-GPU
  # offers with >= 16 GB GPU RAM (BensPC's card, where y1t was planned), compute capability >= 7.5 and CUDA 12.8 drivers
  # (torch 2.11 cu128), the rent kit's filter, <= $MAXDPH/h, <= $MAXNET/GB, not a failed host, and an estimated time that
  # fits: chain minutes = REFMIN x max(1, REFTF / its TFLOPS) (inferred scaling from an RTX 5090) at most 120, and
  # (chain + 20 minutes of setup) x $/h at most the cap less $0.30.
  # Prints: id dph gpu host machine cuda down$/GB up$/GB tflops tflops-per-$/h estimated-chain-minutes
  vast search offers "num_gpus=1 gpu_ram>=16 reliability>=0.98 rentable=true cpu_cores>=8 disk_space>=60 inet_down>=200 compute_cap>=750 cuda_max_good>=12.8 direct_port_count>=1" -o dph --raw < /dev/null 2>/dev/null | "$PYM" -c '
import json, sys
maxdph, maxnet, reftf, refmin, cap = map(float, sys.argv[1:6])
bad = set(sys.argv[6].split())
net = lambda v: 99.0 if v is None else float(v)   # a missing download or upload price counts as too dear
try:
    d = json.load(sys.stdin)
    d = d.get("offers", d) if isinstance(d, dict) else d
except Exception:
    sys.exit(0)
rows = []
for o in d:
    p = float(o.get("dph_total") or 0); tf = float(o.get("total_flops") or 0)
    if p <= 0 or tf <= 0 or p > maxdph or int(o.get("num_gpus") or 1) != 1:
        continue
    if float(o.get("gpu_ram") or 0) < 16000 or float(o.get("compute_cap") or 0) < 750 or float(o.get("cuda_max_good") or 0) < 12.8:
        continue   # raw offers give gpu_ram in MB; checked here too, not only in the search query
    if str(o.get("host_id")) in bad or str(o.get("machine_id")) in bad:
        continue
    if net(o.get("inet_down_cost")) > maxnet or net(o.get("inet_up_cost")) > maxnet:
        continue
    est = refmin * max(1.0, reftf / tf)
    if est > 120 or (est + 20) / 60 * p > cap - 0.30:
        continue
    rows.append((tf / p, p, tf, est, o))
rows.sort(key=lambda r: -r[0])
if rows:
    r, p, tf, est, o = rows[0]
    print(o.get("id"), round(p, 4), str(o.get("gpu_name")).replace(" ", "_"), o.get("host_id"), o.get("machine_id"),
          o.get("cuda_max_good"), o.get("inet_down_cost"), o.get("inet_up_cost"), round(tf, 1), round(r, 1), int(est + 0.5))
' "$MAXDPH" "$MAXNET" "$REFTF" "$REFMIN" "$CAP" "$(awk '$1=="FAILHOST"{printf "%s ", $2}' "$VS")" | grep .
}
sshto() { S=on; }   # HOSTN and PORT are set: sx can reach the instance
halt() {  # a problem once this task's instance is known: the last pass copies what it can and destroys; earlier passes leave it
  [ -n "$LAST" ] && { FORCE=1; finish "STOP at the $DLW: $*"; }
  stop "STOP: $*; the instance is left for the next pass"
}
rv() { sx "bash ~/tree/$KR/bov.sh $*" < /dev/null 2>&1; }
getstate() { ST=$(rv state); echo "$ST" | grep -q '^END-STATE' && { echo "$ST" > "$R/state-last.txt"; return 0; }; return 1; }

# ---- the end of a run: copy back, check, destroy, write RESULTS-vast.md
dest() { case "$1" in
  "$D"/*) echo "$R/${1#"$D"/}" ;;
  tr/train398r.json) echo "$R/train398r.json" ;;
  tr/adapter398r.pt) echo "$MA/adapter398r.pt" ;;
  eval/*|eval_plain/*) echo "$R/$1" ;;
  h1/*) echo "$RH/${1#h1/}" ;;
  W/h1_*) echo "$RH/${1#W/}" ;;
  W/*) echo "$R/${1#W/}" ;;
  *) echo "" ;;
esac; }
collect() {  # copies every file the rental's manifest lists; prints 0 when all arrived intact, else what failed
  local t m bad=0 sha size f d
  t=$(mktemp -d); mkdir -p "$t/f"
  rv manifest > "$t/raw.txt"
  grep -q '^END-MAN' "$t/raw.txt" || { rm -rf "$t"; echo "no manifest from the rental"; return; }
  grep '^MAN ' "$t/raw.txt" > "$t/man.txt"
  SXT=600 sx "bash ~/tree/$KR/bov.sh pack" < /dev/null 2>/dev/null | tar -x -C "$t/f" 2>/dev/null
  while read -r m sha size f; do
    d=$(dest "$f"); [ -n "$d" ] || continue
    if [ "$(shasum -a 256 "$t/f/$f" 2>/dev/null | cut -c1-64)" = "$sha" ]; then mkdir -p "$(dirname "$d")"; cp "$t/f/$f" "$d"
    else bad=$((bad+1)); echo "not intact: $f" >&2; fi
  done < "$t/man.txt"
  cp "$t/man.txt" "$R/manifest-rental.txt"
  rm -rf "$t"
  [ "$bad" = 0 ] && echo 0 || echo "$bad file(s) not intact"
}
finish() {  # $1 = status line for RESULTS-vast.md. Destroy only after a checked copy (Thread manager's rule for vast kits)
  local status=$1 r id ok=0 s copy=none flag=""
  if [ -n "${S:-}" ]; then
    r=$(collect)
    if [ "$r" != 0 ]; then
      if [ "$(elapsed)" -lt "${COPY2Y1T:-3900}" ]; then note "copy: $r; trying once more"; r=$(collect)
      else note "copy: $r; no time for a second try before the watcher's alarm"; fi
    fi
    if [ "$r" = 0 ]; then copy=ok
      note "copied back $(grep -c '^MAN ' "$R/manifest-rental.txt") files listed by the rental; every one matches its sha256 there"
      echo "COLLECTED $(date +%s) $(curid) $status" >> "$VS"
    else copy=bad; note "COPY-CHECK FAIL twice: $r"; fi
  fi
  id=$(curid)
  if [ -z "$id" ]; then ok=1
  elif [ "$copy" = ok ] || ! grep -q "^UP [0-9]* $id " "$VS"; then vdestroy "$id" "$status" && ok=1
  elif [ -z "$LAST" ] && [ -z "${FORCE:-}" ]; then
    stop "COPY-FAIL: the copy check failed; the instance is left running for the next pass (nothing destroyed)"
  else
    vstop "$id" "$status" && ok=1
    flag="FLAG-DIRECTOR: instance $id is stopped, not destroyed (the copy check failed); its disk keeps the files"
    status="$status; STOPPED-NOT-DESTROYED"
  fi
  sweep "$id"
  # the watcher pushes files up to 5,120 KiB; a bigger file is pushed as a gzip copy, split into 3,500 KiB parts if needed
  for f in $(find "$R" "$RH" -type f -size +3900k ! -name '*.gz' ! -name '*.gz.part-*' 2>/dev/null); do
    [ -s "$f.gz" ] || [ -s "$f.gz.part-aa" ] && continue
    gzip -9 -c "$f" > "$f.gz"
    if [ "$(wc -c < "$f.gz" | tr -d ' ')" -gt 3993600 ]; then
      split -b 3500k "$f.gz" "$f.gz.part-" && rm -f "$f.gz"
      note "$f is $(wc -c < "$f" | tr -d ' ') bytes: pushed as $(ls "$f.gz.part-"* | wc -l | tr -d ' ') parts $f.gz.part-* (join with cat, then gunzip)"
    else note "$f is $(wc -c < "$f" | tr -d ' ') bytes: pushed as $f.gz ($(wc -c < "$f.gz" | tr -d ' ') bytes)"; fi
  done
  [ -n "$flag" ] && note "$flag"
  results "$status"
  s=$(spent)
  echo "LEDGER-SUGGESTION (for the Director): $(now | cut -c1-16 | tr T ' ') UTC answering from memory: y1t on vast, $(awk '$1=="CREATE"{o[++n]=$3; g[$3]=$5; p[$3]=$6} $1=="DPH"{p[$2]=$3} END{for(k=1;k<=n;k++) printf "%s%s %s at $%s/h", (k>1?"; ":""), o[k], g[o[k]], p[o[k]]}' "$VS"), \$$s, $status"
  [ -n "$flag" ] && echo "$flag"
  [ "$ok" = 1 ] || echo "ACTION NEEDED (FLAG-DIRECTOR): instance $(curid) labelled $LABEL may still be running; its destroy or stop is not confirmed"
  echo "PASS-END $(now)"; exit 0
}
results() {
  local status=$1 f ad mac
  ad=$(awk '$1=="MAN" && $4=="tr/adapter398r.pt" {print $2}' "$R/manifest-rental.txt" 2>/dev/null)
  mac=$(shasum -a 256 "$MA/adapter398r.pt" 2>/dev/null | cut -c1-64)
  lastl() { [ -s "$1" ] && grep . "$1" | tail -"$2" | cut -c1-600 | sed 's/^/    /' || echo "    (no file)"; }
  {
    echo "# y1t vast run record (handoff/kit/y1tvast/pass.sh, job $JOB, kit $PIN, written $(now))"
    echo
    echo "**$status.** No verdict here: the thread scores the sealed DEV marks in VERIFY-y1t.md. Every line below is"
    echo "copied by the script, never retyped. The H1 rows are in $RH (never opened by this job)."
    echo
    echo "## Steps (W/steps.txt; UTC)"
    echo; sed 's/^/    /' "$R/steps.txt" 2>/dev/null; echo
    echo "Minutes per step: $(awk '$2=="start"{split(substr($3,12,8),a,":"); s[$1]=a[1]*60+a[2]+a[3]/60} $2 ~ /^rc=/ && $3=="end" && ($1 in s){split(substr($4,12,8),a,":"); d=a[1]*60+a[2]+a[3]/60-s[$1]; if(d<0) d+=1440; printf "%s %.1f; ", $1, d}' "$R/steps.txt" 2>/dev/null)"
    echo
    echo "## Last lines"
    for f in drafts_log train_log; do echo "- $f.txt:"; echo; lastl "$R/$f.txt" 1; echo; done
    for f in eval_log eval_plain_log; do echo "- $f.txt (last two):"; echo; lastl "$R/$f.txt" 2; echo; done
    for f in h1_A_log h1_B_log; do echo "- $f.txt:"; echo; lastl "$RH/$f.txt" 1; echo; done
    echo "- setup_log.txt (last three):"; echo; lastl "$R/setup_log.txt" 3; echo
    echo "## Machine, money and files"
    echo "- $(grep '^VERSIONS' "$R/checks.txt" 2>/dev/null | head -1) (torch, CUDA, transformers)"
    echo "- $(grep '^GPUNAME' "$R/checks.txt" 2>/dev/null | head -1)"
    echo "- MiniCPM5-1B snapshot $(grep '^BASE ' "$R/setup_log.txt" 2>/dev/null | head -1 | sed 's/^BASE //') (expected .../$MINICPM)"
    echo "- items: $(awk '$1=="ITEMS"{print $2, $3}' "$R/state-last.txt" 2>/dev/null) (train, dev; GATE-RESULT.md has $TRAIN_SHA, $DEV_SHA)"
    echo "- adapter sha256 on the rental: ${ad:-none}; Mac copy ~/y1t-adapter/adapter398r.pt: ${mac:-none} (never pushed)"
    echo "- GPU log (one line a minute: UTC, MiB used, MiB total, W): $(awk '$1=="GPULOG"{sub("^GPULOG ",""); print}' "$R/state-last.txt" 2>/dev/null)"
    echo "- selftests: $(grep -Ec '^CHECK [^ ]+ rc=0 (selftest ok|BM398R-TRAIN-SELFTEST PASS)' "$R/checks.txt" 2>/dev/null) of 4 ok (checks.txt)"
    echo "- credit before the first create: $(awk '$1=="CREDIT"{print $3; exit}' "$VS")"
    echo
    echo "| instance | GPU | \$/h | created (UTC) | gone or stopped (UTC) | hours | download \$ | dollars |"
    echo "|---|---|---|---|---|---|---|---|"
    awk -v t="$(date +%s)" -v gb="$NETGB" -v mx="$MAXNET" '$1=="CREATE"{o[++n]=$3; c[$3]=$2; g[$3]=$5; p[$3]=$6; nc[$3]=($9=="" || $9=="?")?mx:$9}
      $1=="DPH"{p[$2]=$3} $1=="UP"{u[$3]=1} ($1=="GONE" || $1=="STOPPED") && !($3 in e){e[$3]=$2; w[$3]=$1}
      END{for(k=1;k<=n;k++){i=o[k]; x=(i in e)?e[i]:t; d=(i in u)?gb*nc[i]:0; printf "%s %s %s %s %s %s %.2f %.2f %.2f\n", i, g[i], p[i], c[i], (i in e)?e[i]:"-", (i in e)?w[i]:"-", (x-c[i])/3600, d, p[i]*(x-c[i])/3600+d}}' "$VS" |
      while read -r i g p c e w h nd dd; do echo "| $i | $g | $p | $(hms "$c") | $([ "$e" = - ] && echo "not confirmed gone or stopped" || echo "$(hms "$e") ($w)") | $h | $nd | $dd |"; done
    echo
    echo "Total: \$$(spent) of the \$$CAP cap: \$/h x hours from each create until vast stopped listing it (GONE) or it was"
    echo "stopped (STOPPED; its small storage charge is not counted), plus $NETGB GB x the offer's download \$/GB for each"
    echo "instance that answered ssh (a guess at the download size; an adopted instance is priced at \$$MAXNET/GB)."
    echo
    echo "| file | bytes | sha256 |"
    echo "|---|---|---|"
    for f in $(find "$R" "$RH" -type f ! -name 'RESULTS-vast.md' ! -name 'RUN-NOTE-vast.md' ! -name 'vast-state.txt' 2>/dev/null | sort); do
      echo "| $f | $(wc -c < "$f" | tr -d ' ') | $(shasum -a 256 "$f" | cut -c1-64) |"; done
    echo
    echo "## Notes (RUN-NOTE-vast.md)"
    echo; sed 's/^/    /' "$NOTE"
  } > "$R/RESULTS-vast.md"
  note "wrote RESULTS-vast.md: $status"
}

[ "$MODE" = info ] || echo "y1t vast pass, job $JOB ($MODE), kit $PIN, start $(now)"
case "$MODE" in first|next|last|guard|info) ;; *) echo "STOP: mode '$MODE' is not first, next, last, guard or info"; exit 0;; esac
DLW="last pass"; [ "$MODE" = guard ] && DLW="guard (${GUARDWHY:-?})"
# info (for guard.sh): spent, this task's instance, its $/h, its time cap, its ssh host and port, whether the chain is done
if [ "$MODE" = info ]; then
  i=$(curid); echo "$(spent) ${i:-none} $(dphof "$i") $(tcap "$i") $(awk -v i="$i" '$1=="UP" && $3==i {h=$4; p=$5} END{print (h?h:"-"), (p?p:"-")}' "$VS") $(grep -q "^STOPPED [0-9]* $i\$" "$VS" && echo stopped || echo live)"; exit 0
fi
# the notes and the vast state come first, so that every exit below can say what it leaves running
mkdir -p "$R" "$RH"
[ -s "$NOTE" ] || git show "origin/builder-outbox:$NOTE" > "$NOTE" 2>/dev/null || : > "$NOTE"
[ -s "$NOTE" ] || echo "# y1t vast run notes (handoff/kit/y1tvast/pass.sh; UTC; one line per event)" > "$NOTE"
[ -s "$VS" ] || git show "origin/builder-outbox:$VS" > "$VS" 2>/dev/null || : > "$VS"
kdclean() { case "$KD" in */y1tkit.??????) rm -rf "$KD" ;; esac; }   # only the job block's temporary copy of the kit
trap kdclean EXIT
onalarm() { note "ALARM: the watcher's time limit reached this pass"; pending "the watcher's alarm"; echo "PASS-END $(now)"; exit 0; }
trap onalarm ALRM
# 0. duplicates, data, lock
for b in main builder-outbox; do
  git cat-file -e "origin/$b:$R/RESULTS-vast.md" 2>/dev/null && stop "DUPLICATE: origin/$b has $R/RESULTS-vast.md"
  for f in RESULTS-benspc.md RESULTS-rent.md; do
    git cat-file -e "origin/$b:$R/$f" 2>/dev/null && stop "DUPLICATE: origin/$b has $R/$f (another route ran)"; done
  git show "origin/$b:$R/RUN-NOTE-bo.md" 2>/dev/null | grep -q 'LAUNCH chain' && stop "DUPLICATE: origin/$b's RUN-NOTE-bo.md shows a BensPC chain launch"
done
[ -s "$R/RESULTS-vast.md" ] && stop "DONE: $R/RESULTS-vast.md is already in this worktree"
[ -e "$R/RESULTS-benspc.md" ] && stop "DUPLICATE: this worktree has $R/RESULTS-benspc.md"
grep -q 'LAUNCH chain' "$R/RUN-NOTE-bo.md" 2>/dev/null && stop "DUPLICATE: this worktree's RUN-NOTE-bo.md shows a BensPC chain launch"
case "$(git show "origin/main:$A/gate/GATE-RESULT.md" 2>/dev/null | head -1)" in
  *GATE-PASS*) ;; *) stop "NO-DATA: origin/main:$A/gate/GATE-RESULT.md does not say GATE-PASS";; esac
t=$(git show "$PIN:$D/items_train.jsonl" 2>/dev/null | shasum -a 256 | cut -c1-64)
d=$(git show "$PIN:$D/items_dev.jsonl" 2>/dev/null | shasum -a 256 | cut -c1-64)
[ "$t" = $TRAIN_SHA ] && [ "$d" = $DEV_SHA ] || stop "NO-DATA: the items at $PIN have sha256 $t / $d"
command -v "$VAST" >/dev/null || stop "STOP: the vastai CLI is missing"
[ "$("$PYM" -c 'print(6*7)' 2>/dev/null)" = 42 ] || stop "STOP: no working python 3.12 from uv on the Mac"
[ -f "$KEY" ] && [ -f "$KEY.pub" ] || stop "STOP: no ssh key $KEY (and .pub) on the Mac"
# one pass at a time (the same lock as the BensPC kit, so the two routes never run a pass at once); a lock older than
# 80 minutes is left from a pass the watcher's 75-minute alarm ended. A pass that is not the last leaves the notes to the
# pass that holds the lock; the last pass waits for it up to 20 minutes, because nothing runs after the last pass.
[ -d "$R/.pass-lock" ] && [ -n "$(find "$R/.pass-lock" -maxdepth 0 -mmin +80 2>/dev/null)" ] && rmdir "$R/.pass-lock" && note "removed a lock older than 80 minutes"
k=0
until mkdir "$R/.pass-lock" 2>/dev/null; do
  [ -n "$LAST" ] || { echo "LOCKED: another pass holds $R/.pass-lock; stopping (that pass writes the notes)"; echo "PASS-END $(now)"; exit 0; }
  k=$((k+1)); [ $k -le "${LOCKWAITY1T:-40}" ] || stop "LOCKED: another pass still holds $R/.pass-lock after 20 minutes"
  sleep "${LOCKSLEEPY1T:-30}"
done
trap 'rmdir "$R/.pass-lock" 2>/dev/null; kdclean' EXIT
note "pass start ($MODE); spent so far \$$(spent)"

# 1. the instance
L=$(vlist5) || stop "STOP: vast did not answer (show instances) five times in about 5 minutes; nothing done"
f=$(adopt "$L"); [ -n "$f" ] && stop "DUPLICATE: vast lists $f labelled $LABEL that this task did not create; nothing touched"
ID=$(curid)
# an earlier instance of this task that is still listed never answered ssh (the rent loop moves on only after that):
# nothing is on it, so it is destroyed
for o in $(echo "$L" | awk -v i="$ID" 'NF && $1!=i {print $1}'); do
  grep -q "^UP [0-9]* $o " "$VS" && stop "STOP: instance $o of this task answered ssh earlier and is still listed beside ${ID:-none}; nothing touched"
  vdestroy "$o" "never came up; left from an earlier create" || stop "STOP: instance $o of this task is still listed and its destroy is not confirmed"
done
if [ -n "$ID" ] && ! echo "$L" | awk -v i="$ID" '$1==i {f=1} END{exit f?0:1}'; then
  echo "GONE $(date +%s) $ID" >> "$VS"; note "LOST: instance $ID is no longer listed by vast"
  ID=""; LOST=1
fi
if [ -z "$ID" ]; then
  if grep -q '^COLLECTED ' "$VS"; then S=""; finish "$(awk '$1=="COLLECTED"{$1=$2=$3=""; l=$0} END{sub(/^ +/,"",l); print l}' "$VS") (RESULTS-vast.md written by a later pass)"; fi
  if [ "${LOST:-0}" = 1 ] || grep -q '^UP ' "$VS"; then S=""; finish "LOST: the instance went away before its results were copied; what exists is below"; fi
  [ "$MODE" = first ] || stop "NOTHING: no instance, and only the first pass rents"
  # rent (at most 3 creates in all; each one only after the release re-check)
  while [ -z "$ID" ]; do
    [ "$(ncreate)" -lt $MAXCREATE ] || stop "HOST-FAIL: $MAXCREATE creates made, none came up; nothing left running"
    [ "$(elapsed)" -lt 1800 ] || stop "STOP: no instance up 30 minutes into the pass"
    why=$(released) || stop "NOT-RELEASED: $why; nothing rented"
    s=$(spent); over "$(awk -v s="$s" -v m="$MAXDPH" 'BEGIN{print s+m}')" "$CAP" && stop "BUDGET-STOP: \$$s spent, the cap is \$$CAP; nothing rented"
    grep -q '^CREDIT ' "$VS" || echo "CREDIT $(date +%s) $(credit)" >> "$VS"
    L2=$(vlist); [ "$L2" = ERR ] && stop "STOP: vast did not answer before the create; nothing rented"
    if [ -n "$L2" ]; then
      # a labelled instance is listed already: only one that a lost create reply made is used; anything else stops here
      f=$(adopt "$L2"); [ -n "$f" ] && stop "DUPLICATE: vast lists $f labelled $LABEL before the create; nothing rented"
      cid=$(curid)
      { [ -n "$cid" ] && echo "$L2" | awk -v i="$cid" '$1==i {f=1} END{exit f?0:1}'; } || stop "DUPLICATE: an instance labelled $LABEL is listed before the create ($(echo "$L2" | awk '{printf "%s ", $1}')); nothing rented"
      oh=$(awk -v i="$cid" '$1=="CREATE" && $3==i {print $7}' "$VS"); om=$(awk -v i="$cid" '$1=="CREATE" && $3==i {print $8}' "$VS")
      note "using instance $cid (made by an earlier create call of this pass) instead of a new create; waiting up to $RUNWAIT s for it to run"
    else
      o=$(offer) || stop "NO-OFFER: no 1-GPU offer with >= 16 GB at <= \$$MAXDPH/h and <= \$$MAXNET/GB passes the filter with a time that fits; nothing rented"
      set -- $o; oid=$1; odph=$2; og=$3; oh=$4; om=$5; onet=$7; oest=${11}
      note "offer $oid: $og, $9 TFLOPS, at \$$odph/h (${10} TFLOPS per \$/h, the best that fits; estimated chain ${11} minutes), host $oh, machine $om, CUDA $6, download \$$7/GB, upload \$$8/GB"
      echo "CALL $(date +%s) $oid" >> "$VS"
      c=$(vast create instance "$oid" --image "$IMAGE" --disk 60 --label "$LABEL" --ssh --direct --raw < /dev/null 2>/dev/null | "$PYM" -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print("OK" if d.get("success") else "FAIL", d.get("new_contract"))
except Exception:
    print("FAIL none")
')
      set -- $c; cid=${2:-none}
      if [ "$1" = OK ] && [ "$cid" != none ]; then
        echo "CREATE $(date +%s) $cid $oid $og $odph $oh $om $onet" >> "$VS"; echo "EST $cid $oest" >> "$VS"
        note "created instance $cid ($og, \$$odph/h); waiting up to $RUNWAIT s for it to run"
      else
        # the reply can be lost while vast still makes the instance: look for it for 2 minutes before trying another host
        cid=""; k=0
        while [ $k -lt "${ADOPTWAITY1T:-120}" ]; do
          sleep "$POLL"; k=$((k+POLL))
          L3=$(vlist); { [ "$L3" = ERR ] || [ -z "$L3" ]; } && continue
          f=$(adopt "$L3" "$oh $om $onet"); [ -n "$f" ] && stop "DUPLICATE: vast lists $f labelled $LABEL after the create; nothing more rented"
          cid=$(curid); [ -n "$cid" ] && break
        done
        [ -n "$cid" ] || { echo "FAILHOST $oh" >> "$VS"; note "create on offer $oid did not answer OK and no instance appeared in 2 minutes"; continue; }
        note "create on offer $oid did not answer OK, but instance $cid appeared with this task's label; waiting up to $RUNWAIT s for it to run"
      fi
    fi
    t=0; st=""
    while [ $t -lt "$RUNWAIT" ]; do
      sleep "$POLL"; t=$((t+POLL))
      line=$(vlist | awk -v i="$cid" '$1==i'); st=$(echo "$line" | awk '{print $2}')
      [ "$st" = running ] && break
    done
    if [ "$st" = running ]; then
      set -- $line; HOSTN=$4; PORT=$5; sshto
      echo "DPH $cid $3" >> "$VS"
      k=0; up=""
      while [ $k -lt "$SSHWAIT" ]; do
        [ $((k % 80)) -lt 15 ] && vast attach ssh "$cid" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1
        up=$(SXT=40 sx 'echo ok' < /dev/null 2>/dev/null | grep -x ok); [ "$up" = ok ] && break; sleep 15; k=$((k+15)); done
      if [ "$up" = ok ]; then echo "UP $(date +%s) $cid $HOSTN $PORT" >> "$VS"; ID=$cid; note "instance $cid is running and answers ssh"; break; fi
      note "instance $cid runs but does not answer ssh after $SSHWAIT s"
    else note "instance $cid is '$st', not running, after $RUNWAIT s"; fi
    echo "FAILHOST $oh" >> "$VS"; echo "FAILHOST $om" >> "$VS"
    vdestroy "$cid" "did not come up" || stop "STOP: instance $cid did not come up and its destroy is not confirmed; nothing more rented"
  done
else
  line=$(echo "$L" | awk -v i="$ID" '$1==i'); set -- $line
  if ! grep -q "^UP [0-9]* $ID " "$VS"; then
    # it never answered ssh as this task's instance (a pass ended between its create and its ssh check, or its destroy
    # was not confirmed): nothing is on it, it is never used, and it is destroyed
    echo "FAILHOST $(awk -v i="$ID" '$1=="CREATE" && $3==i {print $7}' "$VS")" >> "$VS"
    vdestroy "$ID" "never came up" && stop "HOST-FAIL: instance $ID never answered ssh ('$2'); destroyed; only the first pass's own loop rents"
    stop "HOST-FAIL: instance $ID never answered ssh ('$2') and its destroy is not confirmed"
  fi
  if [ "$2" != running ]; then
    [ -n "$LAST" ] && { S=""; FORCE=1; finish "LOST: instance $ID is '$2', not running, at the $DLW"; }
    stop "WAIT: instance $ID is '$2', not running; nothing done this pass"
  fi
  HOSTN=$4; PORT=$5; sshto
  echo "DPH $ID $3" >> "$VS"
fi
DPH=$(dphof "$ID"); over 0 "$DPH" && DPH=$MAXDPH

[ "$MODE" = guard ] || ensure_guard
# 2. the tree on the rental (made once from the pinned commit)
P0=$(SXT=60 sx 'if [ -f ~/tree/W/tree-pin.txt ]; then cat ~/tree/W/tree-pin.txt; elif [ -e ~/tree/W/chain.started ]; then echo STARTED-NO-PIN; elif [ -d ~/tree ]; then echo NO-PIN; else echo NO-TREE; fi' < /dev/null 2>/dev/null | grep . | tail -1)
echo "tree: $P0"
case "$P0" in
  "$PIN") ;;
  NO-TREE|NO-PIN)
    [ "$MODE" = guard ] && { FORCE=1; finish "GUARD-STOP (${GUARDWHY:-?}): no tree on the rental yet; nothing ran"; }
    git archive "$PIN" scripts artifacts/claude-e2e331-dev-20260924 artifacts/claude-y1t-20260926 \
      artifacts/claude-spare401-20260926/panel/turns.jsonl artifacts/claude-spare401-20260926/SEAL-spare401.sha256.txt \
      handoff/kit/y1tvast | SXT=600 sx 'mkdir -p ~/tree && tar -xf - -C ~/tree' 2>&1
    ps="${PIPESTATUS[0]} ${PIPESTATUS[1]}"
    [ "$ps" = "0 0" ] || halt "streaming the tree failed (git archive, ssh tar: $ps)"
    m=$(rv mark-tree "$PIN"); echo "$m"; note "tree ~/tree made from $PIN ($P0): $m" ;;
  "") halt "no answer from the rental over ssh" ;;
  *) halt "the rental's tree is '$P0', not $PIN" ;;
esac
want=$(cd "$KD/$KR" && shasum -a 256 bov.sh chain.sh | awk '{print $1}' | tr '\n' ' ')
got=$(rv kithash | grep -E '^[0-9a-f]{64} ' | awk '{print $1}' | tr '\n' ' ')
[ "$want" = "$got" ] || { echo "want $want"; echo "got  $got"; halt "the kit on the rental does not match $PIN"; }
echo "kit on the rental matches $PIN"

# a process that should be running is gone (the rental may have restarted) when two looks at least DIEDWAIT s apart
# both find none of it: $1 = the process count from the state, $2 = what died
dead0=""
died() {
  [ "$1" = 0 ] || { dead0=""; return 1; }
  [ -n "$dead0" ] || { dead0=$(date +%s); return 1; }
  [ $(( $(date +%s) - dead0 )) -ge "${DIEDWAITY1T:-60}" ] || return 1
  note "DIED: $2 is not running any more and did not write its end file (two looks at least ${DIEDWAITY1T:-60} s apart)"
}

# 3. setup (once, detached; about 5 to 10 minutes)
getstate || halt "no state from the rental"
[ "$MODE" = guard ] && [ "$(sv CHAIN | cut -d' ' -f1)" != "started=1" ] && { FORCE=1; finish "GUARD-STOP (${GUARDWHY:-?}): the chain was never launched (setup $(sv SETUP | cut -d' ' -f2-))"; }
case "$(sv SETUP)" in "started=0"*) note "setup: $(rv setup-start)" ;; esac
while :; do
  getstate || { sleep "$S1"; getstate || halt "no state from the rental twice"; }
  case "$(sv SETUP)" in
    *"rc=0") break ;;
    *"rc=-") died "$(sv SETUPPROC)" "setup" && { FORCE=1; finish "DIED: setup stopped without writing setup.done; the chain never started"; } ;;
    *) FORCE=1; finish "ENV-FAIL: setup ended $(sv SETUP | cut -d' ' -f2-); the chain never started" ;;
  esac
  [ "$(elapsed)" -lt "$WATCH" ] || { [ -n "$LAST" ] && { FORCE=1; finish "PARTIAL: setup was still running at the $DLW's deadline"; }; stop "RUNNING: setup still running $(sv SETUPLAST | cut -c1-120); the next pass goes on"; }
  s=$(spent); over "$(awk -v s="$s" -v p="$DPH" 'BEGIN{print s+p/4}')" "$CAP" && { FORCE=1; finish "BUDGET-STOP: \$$s spent during setup (cap \$$CAP)"; }
  sleep 30
done
dead0=""
note "setup done: $(sv SETUPLAST | cut -c1-160)"

# 4. checks (once), then the chain (once)
if [ "$(sv CHECKS)" = "- -" ]; then
  c=$(SXT=600 rv checks); echo "$c"
  note "checks: $(echo "$c" | grep -Ec '^CHECK [^ ]+ rc=0 (selftest ok|BM398R-TRAIN-SELFTEST PASS)') of 4 selftests ok; $(echo "$c" | grep '^VERSIONS' | head -1); $(echo "$c" | grep '^GPUNAME' | head -1)"
  getstate || halt "no state from the rental"
fi
if [ "$(sv CHAIN | cut -d' ' -f1)" = "started=0" ]; then
  FORCE=1
  [ "$(sv SEALR)" = "16 16" ] || finish "SEAL-FAIL: SEAL-y1t-rental $(sv SEALR) (needs 16 of 16); nothing launched"
  [ "$(sv SEALH)" = "1 1" ] || finish "SEAL-FAIL: SEAL-y1tH1-runner $(sv SEALH) (needs 1 of 1); nothing launched"
  [ "$(sv SEALP)" = "1 1" ] || finish "SEAL-FAIL: the spare401 panel line $(sv SEALP) (needs 1 of 1); nothing launched"
  [ "$(sv ITEMS)" = "$TRAIN_SHA $DEV_SHA" ] || finish "NO-DATA: the rental's items are $(sv ITEMS); nothing launched"
  [ "$(sv CHECKS)" = "4 4" ] || finish "CHECK-FAIL: selftests $(sv CHECKS) (needs 4 of 4; checks.txt); nothing launched"
  [ "$(sv PY)" = 0 ] || finish "BUSY: $(sv PY) y1t python process(es) already on the rental; nothing launched"
  [ "$(sv DISK)" -ge 8 ] 2>/dev/null || finish "NO-DISK: the rental has $(sv DISK) GB free and the run needs 8 GB; nothing launched"
  # the chain's own cap: the minutes the money left pays for, keeping 15 minutes for the copy and destroy; at most 180
  # and never past the time cap (less 5 minutes), so the chain stops itself even if no pass or guard is running
  capm=$(awk -v c="$CAP" -v s="$(spent)" -v p="$DPH" -v t="$(( ( $(tcap "$ID") - $(date +%s) ) / 60 - 5 ))" 'BEGIN{m=int((c-s)/p*60)-15; if(m>180)m=180; if(t<m)m=t; print m}')
  [ "$capm" -ge 45 ] || finish "BUDGET-STOP: \$$(spent) spent; the money and time caps leave $capm minutes of chain, under 45; nothing launched"
  unset FORCE
  out=$(rv launch-chain "$capm"); echo "$out"; note "$(echo "$out" | tr '\n' ';')"
  if ! echo "$out" | grep -q '^LAUNCH chain .*rc=0 pid='; then
    # the reply can be lost while the chain still started: look again before deciding (never destroy a running chain)
    sleep 20; getstate || { sleep "$S1"; getstate; } || halt "no state from the rental after the launch"
    [ "$(sv CHAIN | cut -d' ' -f1)" = "started=1" ] || { FORCE=1; finish "STOP: the chain launch did not report rc=0 and the rental shows no chain"; }
    note "the launch reply was not rc=0, but the rental shows the chain started: $(sv CHAIN)"
  fi
fi

# 5. watch until the chain is done, this pass's deadline or the money cap
lastn=0; fails=0
while :; do
  if getstate; then fails=0; else
    fails=$((fails+1)); [ $fails -lt 5 ] || { [ -n "$LAST" ] && { FORCE=1; finish "NO-ANSWER: no answer from the rental for 5 minutes at the $DLW"; }; stop "STOP: no answer from the rental for 5 minutes; the instance is left for the next pass"; }
    sleep "$S1"; continue; fi
  echo "$ST" > "$R/state-last.txt"
  cur=$(echo "$ST" | awk '$1=="STEP" && $3=="start" {s=$2} END {print s}')
  lage=$(echo "$ST" | awk -v s="$cur" '$1=="LAST" && $2==s {sub("age=","",$3); sub("m","",$3); print $3}')
  case "$(sv CHAIN)" in *"done=1"*) note "chain done: $(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=/' | awk '{printf "%s %s; ", $2, $3}')"; break ;; esac
  died "$(sv CHAINPROC)" "the chain (remote/chain.sh)" && { DIED=1; break; }
  s=$(spent)
  if over "$(awk -v s="$s" -v p="$DPH" 'BEGIN{print s+p/4}')" "$CAP"; then
    note "MONEY: \$$s spent, cap \$$CAP; asking the chain to stop: $(SXT=260 rv stop-chain money-cap | tr '\n' ';')"; MONEY=1; break; fi
  if [ "$(date +%s)" -ge "$(tcap "$ID")" ]; then
    note "TIME: the time cap $(hms "$(tcap "$ID")") has passed; asking the chain to stop: $(SXT=260 rv stop-chain time-cap | tr '\n' ';')"; TIMEUP=1; break; fi
  if [ "$(elapsed)" -ge "$WATCH" ]; then
    if [ -n "$LAST" ]; then note "$DLW deadline: asking the chain to stop: $(SXT=260 rv stop-chain "$MODE-deadline" | tr '\n' ';')"; DEADLINE=1; break; fi
    stop "RUNNING: step ${cur:-?}, log age ${lage:-?} min, GPU $(sv GPU), \$$s spent; the chain keeps running for the next pass"
  fi
  if [ $(( $(elapsed) / 600 )) -gt $lastn ]; then lastn=$(( $(elapsed) / 600 ))
    note "running: step ${cur:-?}, log age ${lage:-?} min, GPU $(sv GPU), \$$s spent; $(echo "$ST" | grep "^LAST ${cur:-none} " | cut -c1-160)"; fi
  sleep "$S1"
done
getstate && echo "$ST" > "$R/state-last.txt"
nok=$(echo "$ST" | awk '$1=="STEP" && $3=="rc=0"' | wc -l | tr -d ' ')
bad1=$(echo "$ST" | awk '$1=="STEP" && $3 ~ /^rc=/ && $3!="rc=0" {print "step " $2 " ended " $3; exit}')
if [ "$nok" = 6 ]; then status="COMPLETE: all 6 steps ended rc=0"
else status="PARTIAL: $nok of 6 steps ended rc=0${bad1:+; $bad1}"; fi
[ -n "${MONEY:-}" ] && status="BUDGET-STOP, $status"
[ -n "${TIMEUP:-}" ] && status="TIME-STOP, $status"
[ -n "${DEADLINE:-}" ] && { [ "$MODE" = guard ] && status="GUARD-STOP (${GUARDWHY:-?}), $status" || status="LAST-PASS-STOP, $status"; }
[ -n "${DIED:-}" ] && status="DIED (the chain stopped running without writing chain.done; the rental may have restarted), $status"
[ -n "${MONEY:-}${DEADLINE:-}${DIED:-}${TIMEUP:-}" ] && FORCE=1
finish "$status"
