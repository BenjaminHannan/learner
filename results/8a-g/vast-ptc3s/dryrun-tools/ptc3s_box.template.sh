# PC-queue job 8aPTC3S on one rented RTX 4090 (written 2026-10-13). Runs on a Vast GPU box as `bash -c "export NAME=VALUE ...; <this file>" cio`, like custom_io/box/box.sh
# (branch claude/project-thread-x2cm2v). It keeps box.sh's say()/die()/emit() conventions and its RBEGIN|R||REND log protocol, so vast.py collect / collectck read it.
#
# THE JOB (PC queue file results/8a-g/pc-job-cards/ptc/8aPTC3S-pc.txt): arm PTC = the plain 3M step model trained with the calculator (calc_train), seed 400, rung 3M,
# 24,000 updates, accum PTC=16, eg_embed (frozen EmbeddingGemma 2 front), caps_b3s.json, long-chunk pool p10-rung30-s400-a64-L. Nothing is decided here: the queue file's two
# job lines (the g8a-data line and the g8a line) become command lines through custom_io.local_runner's OWN parse_queue() and command(), imported from the assembled tree, so the
# flags are the ones the PC runner would pass (only {WORK} and the output folders differ). Code = custom_io at 74d6e92c75 (src-b3g2) + the six PTC overlay files of branch
# claude/project-thread-yha868 at c2bf1a71c7, assembled and sha256-checked the way install_ptc.ps1 does (every package file, base and overlay), then ptccheck.py on the CPU.
#
# STAGES (printed as `=== STAGE name time`): setup (packages) -> code (fetch by sha, assemble, verify, ptccheck, freeze) -> gemma (EmbeddingGemma 2 + `eg check cuda`)
#   -> data (custom_io.g8a.get_data, the PC's g8a-data line) -> skills (200k curriculum, hash checked) -> train (the job; pool, caps and training all happen inside it) -> result.
# MARKERS in the container log: CIO START, STAGE ..., TICK ..., GUARD ..., CODE-ID ..., CMD ..., PTC3S TRAIN START, PTC3S JOB END rc=N, RESULT-SUMMARY ..., RBEGIN/R|/REND (the
#   result tarball, name 8aPTC3S-3M-s400), PTC3S RESULT PRINTED, part ckN ..., CKFULL|, CKDONE|N, CIO DONE, CIO-FAIL <why> (then the box waits FAIL_SLEEP: read it, destroy it).
# No credential is on the box and nothing listens. GitHub (public repo) and Hugging Face (ungated model and dataset) are reached anonymously.
#
# ENV (vast.py create --env "NAME=VALUE ..."; no spaces inside a value). The first five are box.sh's interface:
#   MAXH        hard stop, hours since the script started (setup included); kills the running step's process group; default 6. train.py saves nothing before its end
#               (no resume), so a MAXH stop in training means no result: it is a cost cap, not a plan. Keep MAXH x (dollars per hour) <= 4.
#   END_SLEEP   seconds the box stays up after everything is printed (billed; destroy it as soon as you have collected); default 600.
#   FAIL_SLEEP  seconds the box stays up after a CIO-FAIL so the log can be read (billed); default 1800.
#   TFVER       transformers version; default 5.19.0 (the PC's; EmbeddingGemma 2 needs >= 5.19).
#   EG          must be 1 (default 1): the job has eg_embed. EG=0 refuses.
#   DPH, PROJ_CAP_USD, GUARD_STEP, EXTRA_H   speed guard. DPH = dollars per hour of this offer (dph_total from search; 0 = guard off). At the first train line with
#               step >= GUARD_STEP (default 1000) it projects total cost = (hours up + remaining updates at the measured speed + EXTRA_H final-evaluation hours) x DPH; above
#               PROJ_CAP_USD (default 4.0) it prints GUARD STOP and kills the job. EXTRA_H default 0.5 (a guess, untested).
#   EXPORT_CK   1 (default): print checkpoint.pt (about 16 MB) in 3 MB parts after the result, PACE seconds apart (100), CK_ROUNDS times (3: a collectck started up to 15 minutes after the result line still gets every part; each round is 5 parts = about 8 minutes of box time).
#   PTC_DRY, PTC_DRY_EXTRA, PTC_DRY_EG, STOP_AFTER, J, TICK_EVERY   CPU dry-run hooks (DRYRUN.md). Never set on Vast. J is the work root (default /job).
#
# PROFILE=1 (default 0; added 2026-10-14): the one-hour GPU shake-out and profiling rental instead of the job. Stages setup, code, gemma, data, skills run exactly as above; then, in
# place of `train`, stage prof: (1) fetch the profiling harness (branch claude/project-thread-yha868, results/8a-g/speedup, commit PROF_SHA, prof_train.py sha256 checked); (2) the
# production-speed smoke: the queue-built job command with --steps PROF_JOB_STEPS (300) and --train-extra '--log-every 50', output in its own folder (profjob), under a timeout;
# it builds the real pool and prints seconds per update and the time of the final evaluation (PROF-JOB lines); (3) six harness runs on that pool (profile, bench, equiv, E4 trace, and
# two B3G2 runs), each under its own timeout, a failure logged and not fatal; (4) the outputs printed as two RBEGIN blocks, profjob and profrun (names in RUNBOOK.md, PROFILE
# rental), then PROF RESULT PRINTED, PROF DONE, CIO DONE (or CIO-FAIL when a step failed or MAXH was reached) and a sleep. The speed guard is off, ck_export is not used.
#   PROFILE      0 (default) or 1. Defaults in PROFILE mode: MAXH 2, END_SLEEP 300, FAIL_SLEEP 600 (the job's: 6, 600, 1800).
#   PROF_MAXMIN  time budget of stage prof in minutes (default 75), counted from its start; a step that would start with less than PROF_MIN_LEFT seconds (240) of it left is skipped
#                (PROF SKIP line), a running step's timeout is cut to what is left, and the budget never reaches past MAXH minus 7 minutes.
#   PROF_JOB_MIN timeout of the job smoke in minutes (45); PROF_STEP_MIN timeout of each harness run (25); PROF_JOB_STEPS (300); PROF_JOB_TRAIN_EXTRA ('--log-every 50').
#   PROF_COMPILE 1 adds the torch.compile variant (eg_once,sortpad,oldw,compile) to the bench list (default 0).
#   PROF_DRY_ARGS, PROF_DRY_FAIL, PROF_DRY_HANG   CPU dry-run hooks of stage prof: extra harness flags appended to every run (tiny shapes), a step name whose run gets a bad flag,
#                a step name whose run is replaced by `sleep 3600`. Need PTC_DRY=1; never set on Vast. PROFILE=1 with PTC_DRY=1 is refused on a box that has a GPU.
#
# PROF_PLAN=b3sweep (needs PROFILE=1; default plan = the six harness runs above; added 2026-10-14): the cheap B3G2 micro-batch (accum) sweep of results/8a-g/speedup/PREREG-b3g2-accum.md
# plus two speed-only runs of the agent-turn model AT-1. Stages setup, code, gemma, data, skills and the pool-building job smoke are the PROFILE ones (the smoke is shortened to
# PROF_JOB_STEPS=50: it is there to build the pool p10-rung30-s400-a64-L and to keep the pool check). Then ONLY, each under its own timeout and never fatal: h1_b3g2_accumsweep (B3G2 3M,
# accum 32,16,8,4, 10 warm-up and 40 timed updates, 2 rounds, median s/update, peak allocated GB, mean thinker rounds per micro-batch), h2_b3g2_accumcmp (one update on the same 256 rows
# with K pinned: loss difference and gradient cosine of accum 32 against 16, 8, 4), at_g1 (arm AT of custom_io at AT_SHA = the PC's src-at, the PC's queue line 8aAT-3M-s400-pc.txt through
# local_runner's own parse_queue/command, --steps 300 --train-extra '--log-every 20' at accum 32) and at_g2 (the same at the fastest swept accum that is not 32 and peaks at <= 10 GB;
# accum 8 when none qualifies or the sweep failed). AT is measured for speed only (s/update = median of consecutive differences of the train log lines from step 40 on, peak GB, last step
# reached when the timeout ends it); the box stops the AT job when AT/RESULT.json appears (training over; no final evaluation, no readout, no RESULT checks). No PTC stage, no E4, no a_profile.
#   PROF_PLAN    default | b3sweep | b3ab. b3sweep changes only these defaults: MAXH 3, PROF_MAXMIN 150, PROF_JOB_MIN 20, PROF_JOB_STEPS 50.
#
# PROF_PLAN=b3ab (needs PROFILE=1; added 2026-10-14): the B3G2 speed A/B of results/8a-g/speedup/PREREG-b3g2-speed-ab.md. Same stages setup, code, gemma, data, skills and the same pool-building smoke
# (50 updates). Then ONLY, each under its own timeout and never fatal: i1_b3g2_profile (B3G2 3M at accum 4: breakdown, throughput, padding, syncs), i2_b3g2_abequiv (mark 6: the variants tf32, pad64,
# unfused, nosync against the reference on one update) and i3_b3g2_abbench (reference accum 4; B arms accum 8,16,2 and the single variants; 3 interleaved rounds A,B,A,B,A,B; 10 warm-up and 40 timed
# updates; median s/update, A spread, peak GB, dollar lines from DPH), and LAST i4_b3g2_pair (added 2026-10-14): the registered accum-4 against accum-32 loss comparison on the SAME GPU. i4 fetches the PC's
# src-b3g2 (custom_io at B3G2_SHA = 74d6e92c75, the pin list PINS0 of install_g2fa4.py checked against git by gen_box.py), builds the two job commands from the pack's queue lines 8aB3G2A4-pc.txt and
# 8aB3G2A4b32-pc.txt with local_runner's own parse_queue / command (as the job smoke and the AT runs do), changes nothing but --accum B3G2=4 / B3G2=32 and --train-extra (here '--log-every 1' ONLY: no
# --ckpt-every, no --resume, so the unmodified train.py of the pin list runs), and runs them one after the other in their own output folders: accum 4 (timeout PROF_PAIR_A4_MIN = 25 min), then accum 32
# (PROF_PAIR_A32_MIN = 80 min). The box stops each job as soon as its train log reaches step 300 (--steps is not given: the job would otherwise train 24,000 updates and the lr schedule must stay the
# registered one), checks that the process group is gone before the next one starts, and exports each run's train lines as pair_a4_events.jsonl / pair_a32_events.jsonl (B3G2/events.jsonl when the run has
# one, else the train event lines of B3G2/stdout.txt) in the profrun block, with one 'PROF-PAIR' marker line per run (last step, s/update from the elapsed field, nvidia-smi peak memory). The box
# does NOT compare the two runs: that is done offline. i4 is skipped when fewer than PROF_PAIR_NEED_MIN (105 = 25 + 80) minutes of the PROF_MAXMIN budget are left; it is never fatal.
#   b3ab changes only these defaults: MAXH 4.5, PROF_MAXMIN 190, PROF_JOB_MIN 20, PROF_JOB_STEPS 50 (MAXH was 3 and PROF_MAXMIN 120 before i4 was added; b3sweep keeps 3 and 150). PROF_B3P_MIN (15), PROF_ABE_MIN (20),
#   PROF_ABB_MIN (75): timeouts of i1, i2, i3 in minutes. PROF_PAIR_A4_MIN (25), PROF_PAIR_A32_MIN (80), PROF_PAIR_NEED_MIN (105): i4. PROF_PAIR_TRAIN_EXTRA ('--log-every 1') is a CPU dry-run hook.
#   DPH should be the offer's dph_total: abbench prints its money lines from it (0 = no dollar figures); the box prints the rental so far and the MAXH ceiling in dollars.
#   PROF_SWEEP_MIN (45) and PROF_CMP_MIN (15): timeouts of h1 and h2 in minutes; PROF_AT_MIN (40): timeout of each AT run; PROF_AT_STEPS (300); PROF_AT_TRAIN_EXTRA ('--log-every 20');
#   PROF_AT_FROM_STEP (40): the speed is taken from the log lines at and after this step.
set -u
J=${J:-/job}; mkdir -p $J/out $J/res $J/state $J/w $J/work; cd $J || exit 1
R=https://github.com/BenjaminHannan/learner
BASE_SHA=74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6      # custom_io of src-b3g2 (branch claude/project-thread-emwjvn)
OVL_SHA=c2bf1a71c7386396a087e5993a3de4ce8873925d       # branch claude/project-thread-yha868: the PTC package
OVL_DIR=results/8a-g/pc-job-cards/ptc
DP_SHA=3d0afbeadd5f1775c7c92195348bab6f66da767d        # branch claude/data-pool-8b (cloze_long.py's commit; the manifests, web_slice.py and the panel index are the same files as at 12d30d0ce9)
OWN_SHA=8d012f1f97bd8203b15e88e369dc856721e13e6a       # branch claude/8a-own-data
CUR_SHA=57c45293fe7158aae92d017e6a9bd2d87e29dcdf       # branch claude/project-thread-y0sxwe (skills_curriculum; its 200k manifest decides, as in box.sh)
MANIFEST_SHA=e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0    # data_pool/built/own72_MANIFEST.json (the PC's --expect-manifest-sha)
CLOZE_SHA=@@CLOZE_SHA@@       # data_pool/cloze_long.py at 3d0afbeadd
CAPS_PY_SHA=@@CAPS_PY_SHA@@   # g8a/caps.py of 74d6e92c75 (install_ptc.ps1's $CAPS)
CAPS_B3S_SHA=@@CAPS_B3S_SHA@@ # g8a/caps_b3s.json of 74d6e92c75 (the PC's work\b3-inputs copy)
EG2_ST_SHA=197a32965d4b1105faf060417baa899e193fb73cd401f42ec9295234d5553d79       # model.safetensors of google/embeddinggemma-2 at 914f7f89 (Hugging Face API lfs oid)
PROFILE=${PROFILE:-0}
PROF_PLAN=${PROF_PLAN:-default}
if [ "$PROFILE" = 1 ]; then D_MAXH=2; D_END=300; D_FAIL=600; else D_MAXH=6; D_END=600; D_FAIL=1800; fi
[ "$PROFILE" = 1 ] && [ "$PROF_PLAN" = b3sweep ] && D_MAXH=3
[ "$PROFILE" = 1 ] && [ "$PROF_PLAN" = b3ab ] && D_MAXH=4.5
MAXH=${MAXH:-$D_MAXH}; END_SLEEP=${END_SLEEP:-$D_END}; FAIL_SLEEP=${FAIL_SLEEP:-$D_FAIL}; TFVER=${TFVER:-5.19.0}; EG=${EG:-1}
DPH=${DPH:-0}; PROJ_CAP_USD=${PROJ_CAP_USD:-4.0}; GUARD_STEP=${GUARD_STEP:-1000}; EXTRA_H=${EXTRA_H:-0.5}; STEPS=24000
EXPORT_CK=${EXPORT_CK:-1}; PACE=${PACE:-100}; CK_ROUNDS=${CK_ROUNDS:-3}; TICK_EVERY=${TICK_EVERY:-180}
PTC_DRY=${PTC_DRY:-0}; PTC_DRY_EXTRA=${PTC_DRY_EXTRA:-[]}; PTC_DRY_EG=${PTC_DRY_EG:-0}; STOP_AFTER=${STOP_AFTER:-}
PROF_SHA=@@PROF_SHA@@          # branch claude/project-thread-yha868: results/8a-g/speedup/prof (prof_train.py, the GPU profiling harness; PROFILE=1 only)
PROF_DIR=results/8a-g/speedup
PROF_PY_SHA=@@PROF_PY_SHA@@    # sha256 of prof/prof_train.py at PROF_SHA
if [ "$PROF_PLAN" = b3ab ]; then D_PMAX=190; D_PJOBMIN=20; D_PJOBSTEPS=50; D_PLOGE='--log-every 10'      # plan b3ab: as b3sweep; 190 min with i4_b3g2_pair
elif [ "$PROF_PLAN" = b3sweep ]; then D_PMAX=150; D_PJOBMIN=20; D_PJOBSTEPS=50; D_PLOGE='--log-every 10'; else D_PMAX=75; D_PJOBMIN=45; D_PJOBSTEPS=300; D_PLOGE='--log-every 50'; fi      # plan b3sweep: the smoke only builds the pool
PROF_MAXMIN=${PROF_MAXMIN:-$D_PMAX}; PROF_MIN_LEFT=${PROF_MIN_LEFT:-240}; PROF_JOB_MIN=${PROF_JOB_MIN:-$D_PJOBMIN}; PROF_STEP_MIN=${PROF_STEP_MIN:-25}; PROF_JOB_STEPS=${PROF_JOB_STEPS:-$D_PJOBSTEPS}
PROF_JOB_TRAIN_EXTRA=${PROF_JOB_TRAIN_EXTRA:-}; [ -n "$PROF_JOB_TRAIN_EXTRA" ] || PROF_JOB_TRAIN_EXTRA=$D_PLOGE
PROF_COMPILE=${PROF_COMPILE:-0}; PROF_MAX_BYTES=${PROF_MAX_BYTES:-2000000}
PROF_DRY_ARGS=${PROF_DRY_ARGS:-}; PROF_DRY_FAIL=${PROF_DRY_FAIL:-}; PROF_DRY_HANG=${PROF_DRY_HANG:-}
# PROF_PLAN=b3sweep only (see the header): AT-1 = custom_io at AT_SHA (the PC's src-at), pins from the AT10M kit and git, the timeouts and the AT run settings
AT_SHA=@@AT_SHA@@          # branch claude/project-thread-emwjvn: custom_io of src-at (the AT10M kit's SRC_SHA)
AT_CAPS_SHA=@@AT_CAPS_SHA@@   # g8a/caps_b3g2.json (also the file of 74d6e92c75)
PROF_SWEEP_MIN=${PROF_SWEEP_MIN:-45}; PROF_CMP_MIN=${PROF_CMP_MIN:-15}; PROF_AT_MIN=${PROF_AT_MIN:-40}; PROF_AT_STEPS=${PROF_AT_STEPS:-300}; PROF_AT_FROM_STEP=${PROF_AT_FROM_STEP:-40}
PROF_AT_TRAIN_EXTRA=${PROF_AT_TRAIN_EXTRA:-}; [ -n "$PROF_AT_TRAIN_EXTRA" ] || PROF_AT_TRAIN_EXTRA='--log-every 20'
PROF_B3P_MIN=${PROF_B3P_MIN:-15}; PROF_ABE_MIN=${PROF_ABE_MIN:-20}; PROF_ABB_MIN=${PROF_ABB_MIN:-75}      # PROF_PLAN=b3ab only: timeouts of i1, i2, i3 in minutes
PROF_PAIR_A4_MIN=${PROF_PAIR_A4_MIN:-25}; PROF_PAIR_A32_MIN=${PROF_PAIR_A32_MIN:-80}; PROF_PAIR_NEED_MIN=${PROF_PAIR_NEED_MIN:-105}; PROF_PAIR_STEP=${PROF_PAIR_STEP:-300}      # PROF_PLAN=b3ab, stage i4_b3g2_pair: timeouts of the two jobs, the budget needed, the update each job is stopped at
PROF_PAIR_TRAIN_EXTRA=${PROF_PAIR_TRAIN_EXTRA:-'--log-every 1'}      # (changed only by the CPU dry run, with the tiny-shape flags it needs)
B3G2_SHA=@@B3G2_SHA@@      # custom_io of the PC's src-b3g2 (the code of the G2f runs); pins = PINS0 of results/8a-g/pc-job-cards/g2fa4/install_g2fa4.py, read by gen_box.py and checked against git
B3G2_Q_SHA=@@B3G2_Q_SHA@@  # the commit the pack's queue lines come from: 8aB3G2A4-pc.txt (full file sha256 @@B3G2_Q4_FULL@@) and 8aB3G2A4b32-pc.txt (@@B3G2_Q32_FULL@@); their MEM and g8a lines are embedded below
PSTEP_MIN=; AT_G2_ACCUM=
T0=${T0:-$(date +%s)}
W=$J/work; D=$W/data; DB=$W/data_big          # the PC's WORK, with its folder names
S=$J/src-ptc                                   # = the PC's src-ptc (custom_io inside)
QNAME=8aPTC3S-pc; RUN=8aPTC3S-3M-s400
RES=$W/results/$QNAME; O=$RES/$RUN             # = WORK\results\8aPTC3S-pc\8aPTC3S-3M-s400
OV=$J/ovl/$OVL_DIR; B=$J/base/custom_io
TLOG=$O/PTC/stdout.txt                         # the training log the TICK lines read (PROFILE mode: the job smoke's)
OP=$RES/profjob; PE=$RES/profrun; PRAW=$J/profraw   # PROFILE mode: job smoke folder, printed harness outputs, raw harness outputs
SAT=$J/src-at                                  # PROF_PLAN=b3sweep: the PC's src-at (custom_io at AT_SHA)
SB3=$J/src-b3g2                                # PROF_PLAN=b3ab, stage i4: the PC's src-b3g2 (custom_io at B3G2_SHA)
WATCH=
say() { echo "=== $* $(date -u +%FT%TZ)"; }
stage() { echo "$1" > $J/state/stage; echo "$1 $(date -u +%FT%TZ)" >> $J/state/stages.txt; echo "=== STAGE $1 $(date -u +%FT%TZ)"; }
sha() { sha256sum "$1" 2>/dev/null | cut -c1-64; }
# a git or pip step that cannot hang the box silently: timeout + retries + a visible line per failure
retry() { n=$1; shift; for k in $(seq 1 $n); do timeout -k 30 900 "$@" && return 0; say "retry $k/$n failed: $*"; sleep 20; done; return 1; }
fetch_sha() {   # dir sha sparse-dirs... : exactly that commit of the repo, blobs on demand (no dirs = the root files only)
  d=$1; s=$2; shift 2
  rm -rf $d; mkdir -p $d; git -C $d init -q && git -C $d remote add origin $R || return 1
  if [ $# -gt 0 ]; then git -C $d sparse-checkout init --cone && git -C $d sparse-checkout set "$@" || return 1; fi
  retry 4 git -C $d fetch -q --depth 1 --filter=blob:none origin $s && retry 3 git -C $d checkout -q FETCH_HEAD && [ "$(git -C $d rev-parse HEAD)" = "$s" ]
}
kill_cur() {    # stop the running step: its whole process group (runp keeps the leader's pid in state/cur.pid)
  p=$(cat $J/state/cur.pid 2>/dev/null); [ -n "$p" ] || return 0
  kill -TERM -- -$p 2>/dev/null; sleep 15; kill -KILL -- -$p 2>/dev/null; return 0
}
runp() {        # LOG DIR cmd... : run cmd in DIR in its own session, output appended to LOG; MAXH / the guard stop it through kill_cur; returns its status
  lf=$1; dir=$2; shift 2
  echo "$lf" > $J/state/curlog
  [ -e $J/state/maxh ] && { echo "MAXH already reached: $* not started" >> "$lf"; return 99; }
  setsid -w bash -c 'echo $$ > "$0"; cd "$1" || exit 1; shift; exec "$@"' $J/state/cur.pid "$dir" "$@" >> "$lf" 2>&1 &
  rp=$!; wait $rp; rc=$?
  rm -f $J/state/cur.pid
  return $rc
}
write_guard() { cat > $J/guard.py <<'PY'
import json, sys
log, t0, now, dph, cap, gstep, steps, extra, maxh = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), float(sys.argv[8]), float(sys.argv[9])
line = None
try:
    for ln in open(log, errors='replace'):
        if '"event": "train"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get('step', 0) >= gstep:
            line = e
            break
except OSError:
    pass
if line is None:
    sys.exit(4)
spu = line['elapsed'] / line['step']                              # seconds per update, from the start of training
up_h = (now - t0) / 3600                                          # hours the box has been up (setup, data and pool included: already paid)
total_h = up_h + (steps - line['step']) * spu / 3600 + extra
usd = total_h * dph
print('GUARD step=%d sec_per_update=%.3f train_total_h=%.2f up_h=%.2f projected_total_h=%.2f dph=%.3f projected_usd=%.2f cap_usd=%.2f' % (
    line['step'], spu, spu * steps / 3600, up_h, total_h, dph, usd, cap), flush=True)
if usd > cap:
    print('GUARD STOP projected %.2f USD > cap %.2f USD' % (usd, cap), flush=True)
    sys.exit(3)
if maxh and total_h > maxh:             # MAXH would kill the job before it ends, and training saves nothing before its end: stop now, not hours later
    print('GUARD STOP projected %.2f h > MAXH %.2f h' % (total_h, maxh), flush=True)
    sys.exit(3)
PY
}
tick() {        # one TICK line: stage, uptime, training progress (or the current step's log size and last line), folder sizes, disk, GPU
  now=$(date +%s); tl=$(grep -h '"event": "train"' $TLOG 2>/dev/null | tail -1)
  prog=$(echo "$tl" | sed -n 's/.*"step": \([0-9]*\), "loss": \([0-9.eE+-]*\), .*"elapsed": \([0-9.]*\).*/step=\1 loss=\2 train_elapsed_s=\3/p')
  if [ -n "$prog" ] && [ "$PROFILE" != 1 ]; then      # projection from the speed so far: hours of training in all, and (with DPH) dollars for the whole box = (hours up + updates left at this speed + EXTRA_H) x DPH
    prog="$prog $(echo "$prog" | tr '=' ' ' | awk -v n=$STEPS -v now=$now -v t0=$T0 -v dph=$DPH -v x=$EXTRA_H '{s=$2; e=$6; if (s > 0) printf "proj_train_h=%.2f proj_usd=%.2f", e/s*n/3600, ((now-t0)/3600 + (n-s)*e/s/3600 + x)*dph}')"
  fi
  if [ -z "$prog" ]; then lf=$(cat $J/state/curlog 2>/dev/null); prog="log=$(basename "$lf" 2>/dev/null) bytes=$(stat -c %s "$lf" 2>/dev/null) last=$(tail -n 1 "$lf" 2>/dev/null | tr -c '[:print:]' ' ' | cut -c1-110)"; fi
  echo "TICK at=$(date -u +%FT%TZ) stage=$(cat $J/state/stage 2>/dev/null) up_min=$(( (now - T0) / 60 )) $prog | mb data8a=$(du -sm $W/data8a 2>/dev/null | cut -f1) skills=$(du -sm $D 2>/dev/null | cut -f1) pools=$(du -sm $W/g8a 2>/dev/null | cut -f1) free=$(df -m $J | awk 'NR==2{print $4}') ram_avail=$(free -m | awk '/^Mem:/{print $7}') | gpu $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader 2>/dev/null)"
}
watch_loop() {  # background: MAXH, the speed guard (once, at GUARD_STEP), a TICK line every TICK_EVERY seconds
  last=0; maxs=$(awk "BEGIN{print int($MAXH*3600)}")
  while true; do
    now=$(date +%s)
    if [ "$MAXH" != 0 ] && [ $((now - T0)) -ge $maxs ]; then      # from now on every step that is running is killed, every 20 s, and runp starts no new one
      [ -e $J/state/maxh ] || say "CIO MAXH $MAXH h reached: stopping the running step (training saves nothing before its end)"; touch $J/state/maxh; kill_cur; sleep 20; continue; fi
    if [ "$PROFILE" != 1 ] && [ "$DPH" != 0 ] && [ ! -f $J/state/guard_done ] && [ -f $O/PTC/stdout.txt ]; then
      python $J/guard.py $O/PTC/stdout.txt $T0 $now $DPH $PROJ_CAP_USD $GUARD_STEP $STEPS $EXTRA_H $MAXH > $J/state/guard.out 2>&1; g=$?
      { [ $g = 0 ] || [ $g = 3 ]; } && { cat $J/state/guard.out; touch $J/state/guard_done; }
      [ $g = 3 ] && { touch $J/state/guard_stop; kill_cur; return 0; }
    fi
    if [ $((now - last)) -ge $TICK_EVERY ]; then last=$now; tick; fi
    sleep 20
  done
}
emit() {        # name dir : the folder as a tar.gz (no *.pt, no stdout.txt: each gets an events file and a tail file) printed as RBEGIN / R| / REND lines with a sha256
  n=$1; d=$2; T=$J/res/$n.tgz
  (cd $d && find . -name stdout.txt | while read -r f; do
     grep -E '"event"|Traceback|Error|error|RESULT' "$f" | cut -c1-4000 > "${f%.txt}.events.txt"; tail -n 100 "$f" | cut -c1-600 > "${f%.txt}.tail.txt"; done)
  tar -czf $T --exclude='*.pt' --exclude=stdout.txt -C "$(dirname "$d")" "$(basename "$d")" 2>/dev/null
  echo "RBEGIN|$n|$(sha $T)|$(stat -c %s $T)"; base64 -w 300 $T | sed "s/^/R|$n|/"; echo "REND|$n"
}
boxfiles() {    # [DIR] : the setup logs and pins travel with the result, in DIR/box/ (default the job's folder RUN)
  bd=${1:-$O}; mkdir -p $bd/box; cp $J/out/*.log $J/out/*.txt $J/out/*.sha256 $J/state/guard.out $J/state/cmd.*.txt $S/PTC-SETUP-OK.txt $bd/box/ 2>/dev/null
  { date -u +%FT%TZ; uname -a; python --version; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>/dev/null; } > $bd/box/box.txt 2>&1
}
summary() {     # [DIR] : one line from RESULT.json (the acceptance fields of RUNBOOK.md); status 0 only if the job and the PTC arm say ok and the final evaluation is in
  python - ${1:-$O} <<'PY'
import json, os, sys
o = sys.argv[1]
def load(p):
    try:
        return json.load(open(os.path.join(o, p)))
    except Exception:
        return {}
r, j = load('PTC/RESULT.json'), load('RESULT.json')
ch = r.get('cap_hits') or {}
print('RESULT-SUMMARY', json.dumps(dict(job_status=j.get('status'), arm_status=r.get('status'), steps=r.get('steps'), n_params=r.get('n_params'), steps_per_s=round(r.get('steps_per_s') or 0, 3),
      train_s=round(r.get('train_s') or 0), wall_s=round(r.get('wall_s') or 0), peak_mem_mib=r.get('peak_mem_mib'), cap_total=ch.get('total'), calc_mismatch=ch.get('calc_mismatch'),
      calc_rows=ch.get('calc_rows'), calc_forced=ch.get('calc_forced'), final_eval=bool(r.get('final_eval')), chain5='chain5' in r, lesions=sorted((r.get('lesions') or {}).keys()))))
sys.exit(0 if j.get('status') == 'ok' and r.get('status') == 'ok' and r.get('final_eval') else 1)
PY
}
ck_export() {   # checkpoint.pt (about 16 MB; Gemma is not in it) through the log: tar.gz, 3 MB parts, one part every PACE seconds, CK_ROUNDS times; vast.py collectck reassembles
  c=$O/PTC/checkpoint.pt
  [ -f $c ] || { echo "CKDONE|0"; return 0; }
  T=$J/res/ck-PTC.tgz; tar -czf $T -C $RES $RUN/PTC/checkpoint.pt || { echo "CKDONE|0"; return 0; }
  full=$(sha $T); rm -f $J/res/ck-PTC.part.*; split -b 3000000 -d -a 3 $T $J/res/ck-PTC.part.
  n=$(ls $J/res/ck-PTC.part.* | wc -l); N=0
  for rd in $(seq 1 $CK_ROUNDS); do
    echo "CKFULL|$RUN/PTC|$full|$n"
    for p in $(ls $J/res/ck-PTC.part.* | sort); do
      k=$((10#${p##*.})); N=$((N + 1))
      echo "RBEGIN|ck$N|$(sha $p)|$(stat -c %s $p)|$RUN/PTC|$k|$n"; base64 -w 480 $p | sed "s/^/R|ck$N|/"; echo "REND|ck$N"
      echo "part ck$N $RUN/PTC $k/$n round $rd"; [ $N -lt $((n * CK_ROUNDS)) ] && sleep $PACE
    done
  done
  echo "CKDONE|$N"
}
die() {
  say "CIO-FAIL $*"; stage failed
  [ -n "$WATCH" ] && kill $WATCH 2>/dev/null
  lf=$(cat $J/state/curlog 2>/dev/null); [ -f "$lf" ] && { echo "--- tail of $lf"; grep -v '^R|' "$lf" | tail -n 15 | cut -c1-400; }
  if [ -d $O ]; then boxfiles; emit $RUN $O; [ "$EXPORT_CK" = 1 ] && [ -f $O/PTC/checkpoint.pt ] && { ck_export; emit $RUN $O; }; fi      # a finished training whose evaluation died still gives its checkpoint
  [ "$PROFILE" = 1 ] && prof_emit          # PROFILE mode: whatever the job smoke and the harness produced so far
  sleep $FAIL_SLEEP; exit 1
}
stop_after() { [ "$STOP_AFTER" = "$1" ] || return 0; say "STOP-AFTER $1 (dry-run hook)"; [ -n "$WATCH" ] && kill $WATCH 2>/dev/null; exit 0; }

# ---- PROFILE=1 only (stage prof, called after the skills stage): the harness, the production-speed smoke, the printed outputs
PFAIL=; PSKIP=; PT0=$T0; PY=$J/prof/$PROF_DIR/prof/prof_train.py
prof_left() {   # seconds left of the stage budget (PROF_MAXMIN from the start of stage prof), and before MAXH minus 7 minutes for the printing
  local now l m
  now=$(date +%s); l=$((PROF_MAXMIN * 60 - (now - PT0)))
  if [ "$MAXH" != 0 ]; then m=$(awk "BEGIN{print int($MAXH * 3600)}"); m=$((m - (now - T0) - 420)); [ $m -lt $l ] && l=$m; fi
  echo $l
}
pstep() {       # NAME OUTFILE ARGS... : one harness run, output PRAW/OUTFILE (+ .md), log PRAW/NAME.log, under its own timeout; never fatal (a failure goes to PFAIL, a skip to PSKIP)
  local nm=$1 of=$2 l t t1 t2 rc
  local -a A DA
  shift 2
  l=$(prof_left)
  if [ -e $J/state/maxh ] || [ "$l" -lt "$PROF_MIN_LEFT" ]; then
    say "PROF SKIP $nm: budget left $l s (minimum $PROF_MIN_LEFT s; PROF_MAXMIN=$PROF_MAXMIN MAXH=$MAXH), MAXH reached: $([ -e $J/state/maxh ] && echo yes || echo no)"
    PSKIP="$PSKIP $nm"; echo "$nm skipped 0 0" >> $J/state/prof_steps.txt; return 0
  fi
  t=$(awk "BEGIN{print int(${PSTEP_MIN:-$PROF_STEP_MIN} * 60)}"); [ $t -gt $l ] && t=$l
  A=("$@" --out "$PRAW/$of"); read -r -a DA <<< "$PROF_DRY_ARGS"; A+=(${DA[@]+"${DA[@]}"})
  [ "$PROF_DRY_FAIL" = "$nm" ] && A+=(--dry-run-bad-flag)
  stage prof-$nm
  say "PROF STEP $nm start: timeout $t s, budget left $l s"
  t1=$(date +%s)
  if [ "$PROF_DRY_HANG" = "$nm" ]; then runp $PRAW/$nm.log $PRAW timeout -k 30 $t sleep 3600
  else runp $PRAW/$nm.log $PRAW timeout -k 30 $t python $PY "${A[@]}"; fi
  rc=$?; t2=$(( $(date +%s) - t1 ))
  echo "$nm $rc $t2 $t" >> $J/state/prof_steps.txt
  say "PROF STEP $nm end rc=$rc secs=$t2$([ $rc = 124 ] && echo ' TIMEOUT')$([ $rc = 137 ] && echo ' KILLED')"
  grep -E -e '-> |throughput:|bench round|E[1-4]|section|FAILED|skipped|Traceback|Error|rror:' $PRAW/$nm.log | tail -n 40 | cut -c1-260
  if [ $rc != 0 ]; then PFAIL="$PFAIL $nm(rc$rc)"; tail -n 6 $PRAW/$nm.log | cut -c1-300; fi
  return 0
}
prof_emit() {   # the job smoke folder and the harness outputs as two RBEGIN blocks, profjob and profrun (once only); die() calls it too
  local f b n sz big
  [ -e $J/state/prof_emitted ] && return 0
  touch $J/state/prof_emitted
  mkdir -p $OP $PRAW; boxfiles $OP
  rm -rf $PE; mkdir -p $PE
  for f in $PRAW/*.json $PRAW/*.md $PRAW/*.jsonl; do
    [ -f "$f" ] || continue; b=${f##*/}
    case $b in *.profiler.json|*trace*) continue;; esac        # the raw profiler output and traces can be huge: only the .profiler.md travels
    cp $f $PE/
  done
  for f in $PRAW/*.log; do [ -f "$f" ] || continue; tail -n 1500 $f | cut -c1-400 > $PE/${f##*/}.tail; done
  cp $J/out/prof_env.txt $J/state/stages.txt $J/state/prof_steps.txt $PE/ 2>/dev/null
  echo "failed=[$PFAIL] skipped=[$PSKIP] maxh_hit=$([ -e $J/state/maxh ] && echo yes || echo no) budget_min=$PROF_MAXMIN pool=${POOL:-none}" > $PE/prof_status.txt
  [ "$PROF_PLAN" = b3sweep ] && echo "plan=b3sweep at_sha=$AT_SHA at_g2_accum=${AT_G2_ACCUM:-none}" >> $PE/prof_status.txt
  find $PE -type f -size +400k ! -name '*.gz' -exec gzip -9 {} +      # (the pair_*_events.jsonl of i4 are about 100 KB each: far below)
  while :; do      # keep the printout far below the 20,000-line window of the Vast log read (3 MB = 10,000 lines of 300 characters): drop the largest .json until the archive fits
    tar -czf $J/res/profrun.chk.tgz -C $RES profrun 2>/dev/null; sz=$(stat -c %s $J/res/profrun.chk.tgz)
    [ "$sz" -le "$PROF_MAX_BYTES" ] && break
    big=$(ls -S $PE/*.json $PE/*.json.gz 2>/dev/null | head -n 1); [ -n "$big" ] || break
    say "PROF WARN profrun archive is $sz bytes, over $PROF_MAX_BYTES: dropping ${big##*/} (its .md stays)"; rm -f $big
  done
  say "PROF printing: block profjob (job smoke folder), block profrun ($(ls $PE | wc -l) files, archive $sz bytes)"
  { emit profjob $OP; emit profrun $PE; } | tee $J/state/emit.out
  n=$(grep -c '^R|' $J/state/emit.out)
  say "PROF RESULT PRINTED blocks=profjob,profrun r_lines=$n (the Vast log read window is 20000 lines) failed=[$PFAIL] skipped=[$PSKIP]"
}
# ---- PROFILE=1 PROF_PLAN=b3sweep only: the B3G2 accum sweep (PREREG-b3g2-accum.md) and two AT-1 speed runs, instead of the six harness runs
prof_b3_helpers() {   # four small python helpers, written once (stdlib only)
  cat > $J/mkcmd_at.py <<'PY'
import json, os, shlex, sys
from pathlib import Path
from custom_io.local_runner import parse_queue, command
queue, work, outroot, code, device, extra = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]), sys.argv[4], sys.argv[5], json.loads(sys.argv[6])
runs = parse_queue(queue, work)
assert [(r[0], r[1]) for r in runs] == [('8a-data', 'g8a-data'), ('8aAT-3M-s400', 'g8a')], [(r[0], r[1]) for r in runs]
state = Path(os.environ['J']) / 'state'
name, kind, args, mem = runs[1]
line = ' '.join(shlex.quote(c) for c in command(kind, args + extra, work, outroot / name, device))
(state / 'cmd.at.txt').write_text(line + '\n')                      # what the PC runner would write as cmd.txt for the AT line
(state / 'cmd.at.mem').write_text('%d\n' % mem)
print('CMD', name, 'mem', mem, 'MiB:', line)
PY
  cat > $J/atcmd.py <<'PY'
import shlex, sys
src, dst, code, out, accum, steps, extra = sys.argv[1:8]
t = shlex.split(open(src).read())
assert t.count('--out') == 1 and t.count('--accum') == 1, t
t[t.index('--out') + 1] = out
i = t.index('--accum') + 1
assert t[i] == 'AT=32', 'the queue line is not accum AT=32: ' + t[i]
t[i] = 'AT=' + accum
t += ['--steps', steps, '--train-extra', extra]                     # the last --steps / --train-extra win in argparse (job.py: --steps is for dry runs)
line = ' '.join(shlex.quote(x) for x in t)
open(dst, 'w').write('#!/bin/bash\ncd %s || exit 1\nexec %s\n' % (shlex.quote(code), line))
print('PROF-AT cmd:', line)
PY
  cat > $J/at_report.py <<'PY'
import json, os, re, statistics, sys
out, name, accum, from_step, steps, rc, how, joblog, outjson, sweepjson = sys.argv[1:11]
accum, from_step, steps = int(accum), int(from_step), int(steps)
def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return {}
def read(p):
    try:
        return open(p, errors='replace').read()
    except OSError:
        return ''
so, jl = read(os.path.join(out, 'AT', 'stdout.txt')), read(joblog)
ev = []
for ln in so.splitlines():
    if '"event": "train"' in ln:
        try:
            ev.append(json.loads(ln[ln.index('{'):]))
        except ValueError:
            pass
res = load(os.path.join(out, 'AT', 'RESULT.json'))
for e in ev:
    print('PROF-AT %s train step=%s loss=%s lr=%s elapsed_s=%s' % (name, e.get('step'), e.get('loss'), e.get('lr'), e.get('elapsed')))
iv = [(b['elapsed'] - a['elapsed']) / (b['step'] - a['step']) for a, b in zip(ev, ev[1:]) if a.get('step', 0) >= from_step and b['step'] > a['step']]
spu = round(statistics.median(iv), 4) if iv else None
d = dict(name=name, accum=accum, steps_asked=steps, from_step=from_step, rc=int(rc), ended=how, last_step=ev[-1]['step'] if ev else None, train_events=[dict(step=e.get('step'), loss=e.get('loss'), elapsed=e.get('elapsed')) for e in ev],
         interval_s_per_update=[round(x, 4) for x in iv], median_s_per_update=spu, n_intervals=len(iv), updates_per_hour=round(3600 / spu) if spu else None)
if ev and ev[0].get('step'):
    d['first_log_s_per_update_incl_start'] = round(ev[0]['elapsed'] / ev[0]['step'], 4)
d['peak_mem_mib'], d['peak_reserved_mib'], d['n_params'], d['train_s'] = res.get('peak_mem_mib'), res.get('peak_reserved_mib'), res.get('n_params'), res.get('train_s')
try:
    used = [int(x) for x in read(os.path.join(out, 'gpu_used_mib.txt')).split()]
except ValueError:
    used = []
d['gpu_used_max_mib_nvidia_smi'] = max(used) if used else None
d['peak_alloc_gb'] = round(res['peak_mem_mib'] / 1024, 2) if res.get('peak_mem_mib') else None
print('PROF-AT %s accum AT=%d: ended=%s (rc %s); last step reached %s of %d' % (name, accum, how, rc, d['last_step'], steps))
if spu:
    print('PROF-AT %s SPEED: %s s/update = median of %d consecutive differences of the log lines from step %d on (%d updates/hour)' % (name, spu, len(iv), from_step, d['updates_per_hour']))
else:
    print('PROF-AT %s NO SPEED: fewer than 2 train log lines at or after step %d (log lines found: %d)' % (name, from_step, len(ev)))
if d['peak_alloc_gb'] is not None:
    print('PROF-AT %s PEAK: %.2f GB allocated (torch max_memory_allocated, RESULT.json peak_mem_mib %s; reserved %s MiB)' % (name, d['peak_alloc_gb'], res.get('peak_mem_mib'), res.get('peak_reserved_mib')))
elif res:
    print('PROF-AT %s PEAK: RESULT.json has no peak_mem_mib (train.py records it on CUDA only); nvidia-smi highest used memory %s MiB (includes cached memory: an upper bound, not the allocated peak)' % (name, d['gpu_used_max_mib_nvidia_smi']))
else:
    print('PROF-AT %s PEAK: no RESULT.json (training did not finish); nvidia-smi highest used memory %s MiB (includes cached memory: an upper bound, not the allocated peak)' % (name, d['gpu_used_max_mib_nvidia_smi']))
sp = ((load(sweepjson).get('sections') or {}).get('accumsweep') or {}).get('points') or {}
b = (sp.get(str(accum)) or {}).get('s_per_update_median')
if b and spu:
    d['b3g2_sweep_s_per_update_same_accum'] = b
    d['ratio_at_over_b3g2_same_accum'] = round(spu / b, 2)
    print('PROF-AT %s RATIO to B3G2 on this box at the same accum %d: %.2fx (B3G2 %.3f s/update from the harness sweep, a free-running mean over its timed updates; AT from train.py log lines; different timers, suggested comparison)' % (name, accum, spu / b, b))
if not spu:
    txt = so + '\n' + jl
    cls = 'CUDA out of memory' if re.search('out of memory', txt, re.I) else 'caps / assertion' if re.search('--caps-file|AssertionError|caps_b3g2', txt) else 'import or file missing' if re.search('ModuleNotFoundError|ImportError|No such file|FileNotFoundError', txt) else 'not classified'
    d['failure_class'] = cls
    print('PROF-AT %s FAILED, no speed (%d train lines): %s. Last lines of the job log:' % (name, len(ev), cls))
    for ln in [x for x in (jl.splitlines() + so.splitlines()) if x.strip()][-8:]:
        print('  | ' + ln[:300])
json.dump(d, open(outjson, 'w'), indent=1)
sys.exit(0 if spu else 1)
PY
  cat > $J/at_pick.py <<'PY'
import json, sys
def say(s):
    print(s, file=sys.stderr)
try:
    pts = json.load(open(sys.argv[1]))['sections']['accumsweep']['points']
    assert isinstance(pts, dict) and pts
except Exception as e:
    say('PROF-AT pick: the sweep json is missing, failed or has no points (%s: %s): accum 8 (the default)' % (type(e).__name__, str(e)[:100]))
    print(8)
    sys.exit(0)
best, rows = None, []
for k, v in pts.items():
    a, s, g = int(k), v.get('s_per_update_median'), v.get('peak_alloc_gb')
    ok = a != 32 and not v.get('oom') and s is not None and g is not None and g <= 10.0
    rows.append('accum %d: %s s/update, peak %s GB, oom %s%s' % (a, s, g, bool(v.get('oom')), '' if ok else ' (not eligible)'))
    if ok and (best is None or s < best[1]):
        best = (a, s, g)
say('PROF-AT pick: ' + '; '.join(rows))
if best:
    say('PROF-AT pick: accum %d is the fastest swept accum other than 32 with peak allocated <= 10 GB (%.3f s/update, %.2f GB)' % best)
    print(best[0])
else:
    say('PROF-AT pick: no swept accum other than 32 qualifies (fits in 10 GB with a speed): accum 8 (the default)')
    print(8)
PY
}
at_prepare() {   # src-at = custom_io at AT_SHA (the PC's src-at), pins checked, the AT job command from the queue file with local_runner's own parse_queue / command; 0 = ready, 1 = not (non-fatal)
  local f h npin=0
  say "PROF-AT code: custom_io at $AT_SHA (branch claude/project-thread-emwjvn, the PC's src-at); pins as in the AT10M kit"
  if ! fetch_sha $SAT $AT_SHA custom_io; then
    say "PROF-AT FAILED: cannot fetch custom_io at $AT_SHA: the AT stages are skipped"; PFAIL="$PFAIL at-fetch"; return 1
  fi
  cat > $J/out/at_pins.txt <<'ATPINS'
@@AT_PINS@@
ATPINS
  while read -r f h; do
    [ "$(sha $SAT/custom_io/$f)" = "$h" ] || { say "PROF-AT FAILED: src-at file $f is not commit ${AT_SHA:0:10}'s (got $(sha $SAT/custom_io/$f), want $h): the AT stages are skipped"; PFAIL="$PFAIL at-pin($f)"; return 1; }
    npin=$((npin + 1))      # (not n: retry() sets a global n)
  done < $J/out/at_pins.txt
  mkdir -p $W/b3-inputs; cp $SAT/custom_io/g8a/caps_b3g2.json $W/b3-inputs/caps_b3g2.json
  [ "$(sha $W/b3-inputs/caps_b3g2.json)" = "$AT_CAPS_SHA" ] || { say "PROF-AT FAILED: the caps_b3g2.json copy is not the pinned one: the AT stages are skipped"; PFAIL="$PFAIL at-caps"; return 1; }
  if ! (cd $SAT && export J PYTHONPATH=$SAT && python $J/mkcmd_at.py $SAT/custom_io/queue_local/8aAT-3M-s400-pc.txt $W $RES $SAT cuda "$PTC_DRY_EXTRA") > $J/out/mkcmd_at.log 2>&1; then
    tail -n 12 $J/out/mkcmd_at.log | cut -c1-400; say "PROF-AT FAILED: the AT job command could not be built from the queue file: the AT stages are skipped"; PFAIL="$PFAIL at-cmd"; return 1
  fi
  cut -c1-1800 $J/out/mkcmd_at.log
  mkdir -p $PRAW; { echo "# AT-1 code on this box: custom_io at $AT_SHA; every file below was sha256-checked"; cat $J/out/at_pins.txt; echo; cat $J/out/mkcmd_at.log; } > $PRAW/at_setup.md
  say "PROF-AT code ok: $npin pinned files match, caps_b3g2.json copied to $W/b3-inputs, the AT command is built (queue file 8aAT-3M-s400-pc.txt, local_runner's own parse_queue and command)"
  return 0
}
at_run() {   # NAME ACCUM : one AT-1 speed run (the real train path, --steps PROF_AT_STEPS) under its own timeout and the stage budget; never fatal; speed only, no readout, no RESULT checks
  local nm=$1 ac=$2 l t t1 t2 rc ao wp how ar
  l=$(prof_left)
  if [ -e $J/state/maxh ] || [ "$l" -lt "$PROF_MIN_LEFT" ]; then
    say "PROF SKIP $nm: budget left $l s (minimum $PROF_MIN_LEFT s; PROF_MAXMIN=$PROF_MAXMIN MAXH=$MAXH), MAXH reached: $([ -e $J/state/maxh ] && echo yes || echo no)"
    PSKIP="$PSKIP $nm"; echo "$nm skipped 0 0" >> $J/state/prof_steps.txt; return 0
  fi
  t=$(awk "BEGIN{print int($PROF_AT_MIN * 60)}"); [ $t -gt $l ] && t=$l
  ao=$RES/at/$nm; rm -rf $ao; mkdir -p $ao
  if ! python $J/atcmd.py $J/state/cmd.at.txt $J/state/cmd.$nm.sh $SAT $ao $ac $PROF_AT_STEPS "$PROF_AT_TRAIN_EXTRA" > $J/out/$nm.cmd.log 2>&1; then
    tail -n 5 $J/out/$nm.cmd.log | cut -c1-400; say "PROF-AT FAILED $nm: the AT command could not be edited"; PFAIL="$PFAIL $nm(cmd)"; return 0
  fi
  cut -c1-1800 $J/out/$nm.cmd.log; cp $J/state/cmd.$nm.sh $ao/cmd.sh.txt
  [ "$PROF_DRY_FAIL" = "$nm" ] && sed -i '$ s/$/ --dry-run-bad-flag/' $J/state/cmd.$nm.sh
  stage prof-$nm
  say "PROF-AT $nm START: arm AT (B3AT) 3M, accum AT=$ac, --steps $PROF_AT_STEPS, --train-extra '$PROF_AT_TRAIN_EXTRA', out $ao; timeout $t s (budget left $l s); the box stops the job when AT/RESULT.json appears (training is over, the final evaluation is not wanted)"
  rm -f $J/state/at_stopped
  ( i=0; while :; do      # peak GPU memory by nvidia-smi (a fallback when the run is cut before RESULT.json), a progress line every 2 minutes, and the stop as soon as training is over
      u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1); [ -n "$u" ] && echo "$u" >> $ao/gpu_used_mib.txt
      if [ -f $ao/AT/RESULT.json ]; then touch $J/state/at_stopped; sleep 2; kill_cur; exit 0; fi
      i=$((i + 1)); [ $((i % 24)) = 0 ] && echo "PROF-AT $nm progress: $(grep -h '"event": "train"' $ao/AT/stdout.txt 2>/dev/null | tail -n 1 | sed -n 's/.*"step": \([0-9]*\), "loss": \([0-9.eE+-]*\), .*"elapsed": \([0-9.]*\).*/step=\1 loss=\2 elapsed_s=\3/p') gpu_used_mib=${u:-none}"
      sleep 5
    done ) &
  wp=$!
  t1=$(date +%s)
  if [ "$PROF_DRY_HANG" = "$nm" ]; then runp $PRAW/$nm.log $SAT timeout -k 30 $t sleep 3600
  else runp $PRAW/$nm.log $SAT timeout -k 30 $t bash $J/state/cmd.$nm.sh; fi
  rc=$?; t2=$(( $(date +%s) - t1 ))
  kill $wp 2>/dev/null; wait $wp 2>/dev/null
  how=ended; [ $rc = 124 ] && how=TIMEOUT; [ -e $J/state/at_stopped ] && how="training finished, job stopped by the box before its final evaluation"; [ -e $J/state/maxh ] && how="MAXH reached"
  echo "$nm $rc $t2 $t" >> $J/state/prof_steps.txt
  say "PROF-AT $nm END rc=$rc secs=$t2 ($how)"
  tail -n 300 $ao/AT/stdout.txt 2>/dev/null | cut -c1-600 > $PRAW/$nm.train.log      # the arm's own stdout (train events, errors); its last 1,500 lines go into the profrun block as $nm.train.log.tail
  python $J/at_report.py $ao $nm $ac $PROF_AT_FROM_STEP $PROF_AT_STEPS $rc "$how" $PRAW/$nm.log $PRAW/$nm.json $PRAW/b3g2_accumsweep.json > $J/out/$nm.report.log 2>&1; ar=$?
  cut -c1-420 $J/out/$nm.report.log
  [ $ar = 0 ] || PFAIL="$PFAIL $nm(no-speed,rc$rc)"
  return 0
}
prof_b3sweep() {   # PROF_PLAN=b3sweep (POOL is set): the B3G2 accum sweep, the pinned-K comparison, then the two AT-1 speed runs; each stage non-fatal under its own timeout
  local B3 ga
  say "PROF PLAN b3sweep: B3G2 accum sweep 32,16,8,4 (PREREG-b3g2-accum.md), K-pinned comparison, AT-1 speed at accum 32 and at the fastest swept accum under 10 GB; no PTC stages, no E4, no a_profile; budget $PROF_MAXMIN min from the start of stage prof"
  prof_b3_helpers
  if [ -f $S/custom_io/g8a/caps_b3g2.json ] && [ -f $S/custom_io/models/b3g2.py ]; then
    B3="--arm B3G2 --rung 3M --accum 32 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json"
    PSTEP_MIN=$PROF_SWEEP_MIN
    pstep h1_b3g2_accumsweep b3g2_accumsweep.json $B3 --sections accumsweep --accum-list 32,16,8,4 --accum-updates 40 --accum-warmup 10 --accum-rounds 2
    grep -E -e 'accumsweep round|accum [0-9]+ round|OOM' $PRAW/h1_b3g2_accumsweep.log 2>/dev/null | tail -n 24 | cut -c1-260
    [ -f $PRAW/b3g2_accumsweep.md ] && { echo "--- b3g2_accumsweep.md"; head -n 60 $PRAW/b3g2_accumsweep.md | cut -c1-300; }
    PSTEP_MIN=$PROF_CMP_MIN
    pstep h2_b3g2_accumcmp b3g2_accumcmp.json $B3 --sections accumcmp --accum-list 32,16,8,4
    grep -E -e 'accumcmp' $PRAW/h2_b3g2_accumcmp.log 2>/dev/null | tail -n 20 | cut -c1-260
    [ -f $PRAW/b3g2_accumcmp.md ] && { echo "--- b3g2_accumcmp.md"; head -n 40 $PRAW/b3g2_accumcmp.md | cut -c1-300; }
    PSTEP_MIN=
  else
    say "PROF B3G2 sweep not made: $S/custom_io/g8a/caps_b3g2.json or $S/custom_io/models/b3g2.py is missing in the assembled tree"; PFAIL="$PFAIL b3g2-files-missing"
  fi
  if at_prepare; then
    at_run at_g1 32
    ga=$(python $J/at_pick.py $PRAW/b3g2_accumsweep.json 2> $J/out/at_pick.log); cat $J/out/at_pick.log | cut -c1-700
    case $ga in ''|*[!0-9]*|0) ga=8;; esac
    AT_G2_ACCUM=$ga
    at_run at_g2 $ga
  else
    PSKIP="$PSKIP at_g1 at_g2"
  fi
}
# ---- PROFILE=1 PROF_PLAN=b3ab, last stage: i4_b3g2_pair
prof_pair_helpers() {   # PROF_PLAN=b3ab, stage i4: two small python helpers, written once (stdlib + local_runner of src-b3g2)
  cat > $J/mkcmd_pair.py <<'PY'
import json, shlex, sys
from pathlib import Path
from custom_io.local_runner import parse_queue, command
q4, q32, work, code, device, extra, tx, o4, o32, d4, d32 = sys.argv[1:12]
work, extra = Path(work).resolve(), json.loads(extra)
NAMES = {'a4': ('8aB3G2A4-3M-s400', '4'), 'a32': ('8aB3G2A4b32-3M-s400', '32')}
toks = {}
for key, q, out, dst in (('a4', q4, o4, d4), ('a32', q32, o32, d32)):
    runs = parse_queue(q, work)
    assert [(r[0], r[1]) for r in runs] == [(NAMES[key][0], 'g8a')], [(r[0], r[1]) for r in runs]
    name, kind, args, mem = runs[0]
    t = list(command(kind, args + extra, work, Path(out), device))      # local_runner's own command, --out = the folder given
    assert t.count('--out') == 1 and t.count('--accum') == 1, t
    i = t.index('--accum') + 1
    assert t[i] == 'B3G2=' + NAMES[key][1], 'the queue line is not accum B3G2=%s: %s' % (NAMES[key][1], t[i])
    old = []
    while '--train-extra' in t:      # the queue's own value (--ckpt-every ... --resume) and any dry-run one are dropped; ours is the only one
        j = t.index('--train-extra'); old.append(t[j + 1]); del t[j:j + 2]
    t += ['--train-extra', tx]
    toks[key] = (t, old, mem)
    line = ' '.join(shlex.quote(x) for x in t)
    open(dst, 'w').write('#!/bin/bash\ncd %s || exit 1\nexec %s\n' % (shlex.quote(code), line))
    print('PROF-PAIR cmd %s (MEM %s MiB; queue --train-extra was %s): %s' % (key, mem, old, line))
def norm(t):
    t = list(t); t[t.index('--out') + 1] = 'OUT'; t[t.index('--accum') + 1] = 'ACCUM'; return t
same = norm(toks['a4'][0]) == norm(toks['a32'][0])
print('PROF-PAIR the two commands are identical except --out and --accum: %s' % ('yes' if same else 'NO'))
sys.exit(0 if same else 1)
PY
  cat > $J/pair_report.py <<'PY'
import json, statistics, sys
key, accum, stepn, ev_path, outjson, rc, how, gpu = sys.argv[1:9]
accum, stepn, rc = int(accum), int(stepn), int(rc)
ev = []
try:
    for ln in open(ev_path, errors='replace'):
        if '"event": "train"' in ln:
            try:
                ev.append(json.loads(ln[ln.index('{'):]))
            except ValueError:
                pass
except OSError:
    pass
try:
    used = [int(x) for x in open(gpu).read().split()]
except (OSError, ValueError):
    used = []
last = ev[-1] if ev else {}
ls, le = last.get('step'), last.get('elapsed')
spu = round(le / ls, 4) if ls and le is not None else None
iv = [(b['elapsed'] - a['elapsed']) / (b['step'] - a['step']) for a, b in zip(ev, ev[1:]) if a.get('step', 0) >= 40 and b['step'] > a['step']]
med = round(statistics.median(iv), 4) if iv else None
d = dict(run=key, accum=accum, stop_step=stepn, rc=rc, ended=how, n_train_lines=len(ev), last_step=ls, elapsed_s_at_last_step=le, s_per_update_elapsed_over_step=spu, median_s_per_update_from_step_40=med, n_intervals=len(iv),
         loss_at_last_step=last.get('loss'), gpu_used_max_mib_nvidia_smi=max(used) if used else None)
json.dump(d, open(outjson, 'w'), indent=1)
print('PROF-PAIR %s accum %d: %s (rc %d); %d train lines, last step %s of %d; elapsed %s s => %s s/update (elapsed/step, includes start-up); median of consecutive differences from step 40 on: %s s/update (%d intervals); loss at last step %s; peak: %s' % (
    key, accum, how, rc, len(ev), ls, stepn, le, spu, med, len(iv), last.get('loss'),
    ('%d MiB nvidia-smi highest used (includes cached memory: an upper bound, not the allocated peak; no RESULT.json on a stopped job)' % max(used)) if used else 'n/a (no nvidia-smi sample)'))
sys.exit(0 if ls and ls >= stepn else 1)
PY
}
pair_alive() { ps -eo args= 2>/dev/null | grep -F -- "--out $1 " | grep -v -F grep > /dev/null; }      # is a job with this --out still running
pair_run() {   # KEY(a4|a32) ACCUM MINUTES : one job (the real train path), stopped by the box at step PROF_PAIR_STEP, own timeout and the stage budget; returns 2 when a process survived (do not go on), else 0 (a failure goes to PFAIL)
  local key=$1 ac=$2 mins=$3 nm=i4_$1 l t t1 t2 rc po wp how ar ev
  l=$(prof_left)
  if [ -e $J/state/maxh ] || [ "$l" -lt "$PROF_MIN_LEFT" ]; then
    say "PROF SKIP $nm: budget left $l s (minimum $PROF_MIN_LEFT s; PROF_MAXMIN=$PROF_MAXMIN MAXH=$MAXH), MAXH reached: $([ -e $J/state/maxh ] && echo yes || echo no)"
    PSKIP="$PSKIP $nm"; echo "$nm skipped 0 0" >> $J/state/prof_steps.txt; return 0
  fi
  t=$(awk "BEGIN{print int($mins * 60)}"); [ $t -gt $l ] && t=$l
  po=$RES/pair/$key; rm -rf $po; mkdir -p $po
  [ "$PROF_DRY_FAIL" = "$nm" ] && sed -i '$ s/$/ --dry-run-bad-flag/' $J/state/cmd.$nm.sh
  cp $J/state/cmd.$nm.sh $po/cmd.sh.txt
  stage prof-$nm
  say "PROF-PAIR $nm START: arm B3G2 3M seed 400, accum B3G2=$ac, --train-extra '$PROF_PAIR_TRAIN_EXTRA', out $po; the box stops the job at step $PROF_PAIR_STEP; timeout $t s (budget left $l s)"
  rm -f $J/state/pair_stopped
  ( i=0; while :; do      # peak GPU memory by nvidia-smi, a progress line every 2 minutes, and the stop as soon as the train log shows step PROF_PAIR_STEP
      s=$(grep -h '"event": "train"' $po/B3G2/stdout.txt 2>/dev/null | tail -n 1 | sed -n 's/.*"event": "train", "step": \([0-9]*\),.*/\1/p')
      if [ $((i % 3)) = 0 ]; then u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1); [ -n "$u" ] && echo "$u" >> $po/gpu_used_mib.txt; fi
      if [ -n "$s" ] && [ "$s" -ge "$PROF_PAIR_STEP" ]; then touch $J/state/pair_stopped; sleep 1; kill_cur; exit 0; fi
      i=$((i + 1)); [ $((i % 60)) = 0 ] && echo "PROF-PAIR $nm progress: step=${s:-none} gpu_used_mib=${u:-none}"
      sleep 2
    done ) &
  wp=$!
  t1=$(date +%s)
  if [ "$PROF_DRY_HANG" = "$nm" ]; then runp $PRAW/$nm.log $SB3 timeout -k 30 $t sleep 3600
  else runp $PRAW/$nm.log $SB3 timeout -k 30 $t bash $J/state/cmd.$nm.sh; fi
  rc=$?; t2=$(( $(date +%s) - t1 ))
  kill $wp 2>/dev/null; wait $wp 2>/dev/null
  how=ended; [ $rc = 124 ] && how=TIMEOUT; [ -e $J/state/pair_stopped ] && how="stopped by the box at step $PROF_PAIR_STEP"; [ -e $J/state/maxh ] && how="MAXH reached"
  echo "$nm $rc $t2 $t" >> $J/state/prof_steps.txt
  say "PROF-PAIR $nm END rc=$rc secs=$t2 ($how)"
  for k in $(seq 1 12); do pair_alive $po || break; sleep 5; done      # the process must be gone before the next job starts (a shared GPU would spoil the timing)
  if pair_alive $po; then
    say "PROF-PAIR $nm process still alive 60 s after the stop: killing it"; pkill -KILL -f -- "--out $po " 2>/dev/null; sleep 10
  fi
  if pair_alive $po; then say "PROF-PAIR $nm PROCESS NOT GONE: the next job is not started"; PFAIL="$PFAIL $nm(alive)"; return 2; fi
  say "PROF-PAIR $nm process gone: yes"
  ev=$po/B3G2/events.jsonl
  if [ -s $ev ]; then cp $ev $PRAW/pair_${key}_events.jsonl; say "PROF-PAIR $nm events: B3G2/events.jsonl ($(wc -l < $ev) lines) -> pair_${key}_events.jsonl"
  else grep -h '"event": "train"' $po/B3G2/stdout.txt 2>/dev/null | sed 's/^[^{]*//' > $PRAW/pair_${key}_events.jsonl; say "PROF-PAIR $nm events: the train lines of B3G2/stdout.txt ($(wc -l < $PRAW/pair_${key}_events.jsonl) lines) -> pair_${key}_events.jsonl"; fi
  tail -n 100 $po/B3G2/stdout.txt 2>/dev/null | cut -c1-600 > $PRAW/pair_${key}.stdout.log
  python $J/pair_report.py $key $ac $PROF_PAIR_STEP $PRAW/pair_${key}_events.jsonl $PRAW/pair_${key}_summary.json $rc "$how" $po/gpu_used_mib.txt > $J/out/$nm.report.log 2>&1; ar=$?
  cut -c1-700 $J/out/$nm.report.log
  if [ $ar != 0 ]; then
    PFAIL="$PFAIL $nm(last-step<$PROF_PAIR_STEP,rc$rc)"; tail -n 6 $PRAW/$nm.log | cut -c1-300
  elif [ $rc != 0 ] && [ ! -e $J/state/pair_stopped ]; then PFAIL="$PFAIL $nm(rc$rc)"
  fi
  return 0
}
prof_b3g2_pair() {   # i4_b3g2_pair, the last stage of PROF_PLAN=b3ab: the registered accum-4 against accum-32 loss comparison on this GPU, 300 updates each, accum 4 first; never fatal; no comparison on the box
  local nm=i4_b3g2_pair l f h npin=0 r
  l=$(prof_left)
  if [ -e $J/state/maxh ] || [ "$l" -lt $((PROF_PAIR_NEED_MIN * 60)) ]; then
    say "PROF SKIP $nm: budget left $l s (needs $PROF_PAIR_NEED_MIN min = $((PROF_PAIR_NEED_MIN * 60)) s; PROF_MAXMIN=$PROF_MAXMIN MAXH=$MAXH), MAXH reached: $([ -e $J/state/maxh ] && echo yes || echo no)"
    PSKIP="$PSKIP $nm"; echo "$nm skipped 0 0" >> $J/state/prof_steps.txt; return 0
  fi
  stage prof-$nm
  say "PROF-PAIR code: custom_io at $B3G2_SHA (the PC's src-b3g2); pins = PINS0 of install_g2fa4.py; queue lines of the pack at ${B3G2_Q_SHA:0:10}; budget left $l s"
  if ! fetch_sha $SB3 $B3G2_SHA custom_io; then
    say "PROF-PAIR FAILED: cannot fetch custom_io at $B3G2_SHA: i4 is skipped"; PFAIL="$PFAIL i4-fetch"; return 0
  fi
  cat > $J/out/b3g2_pins.txt <<'B3PINS'
@@B3G2_PINS@@
B3PINS
  while read -r f h; do
    [ "$(sha $SB3/custom_io/$f)" = "$h" ] || { say "PROF-PAIR FAILED: src-b3g2 file $f is not commit ${B3G2_SHA:0:10}'s (got $(sha $SB3/custom_io/$f), want $h): i4 is skipped"; PFAIL="$PFAIL i4-pin($f)"; return 0; }
    npin=$((npin + 1))
  done < $J/out/b3g2_pins.txt
  cat > $J/out/8aB3G2A4-pc.txt <<'B3Q4'
@@B3G2_Q4@@
B3Q4
  cat > $J/out/8aB3G2A4b32-pc.txt <<'B3Q32'
@@B3G2_Q32@@
B3Q32
  cat > $J/out/b3g2_qpins.txt <<'B3QPINS'
@@B3G2_QPINS@@
B3QPINS
  while read -r f h; do
    [ "$(sha $J/out/$f)" = "$h" ] || { say "PROF-PAIR FAILED: the queue lines $f are not the pinned ones (got $(sha $J/out/$f), want $h): i4 is skipped"; PFAIL="$PFAIL i4-queue($f)"; return 0; }
  done < $J/out/b3g2_qpins.txt
  mkdir -p $W/b3-inputs; cp $SB3/custom_io/g8a/caps_b3g2.json $W/b3-inputs/caps_b3g2.json
  [ "$(sha $W/b3-inputs/caps_b3g2.json)" = "$(awk '$1 == "g8a/caps_b3g2.json" {print $2}' $J/out/b3g2_pins.txt)" ] || { say "PROF-PAIR FAILED: the caps_b3g2.json copy is not the pinned one: i4 is skipped"; PFAIL="$PFAIL i4-caps"; return 0; }
  prof_pair_helpers
  if ! (cd $SB3 && export J PYTHONPATH=$SB3 && python $J/mkcmd_pair.py $J/out/8aB3G2A4-pc.txt $J/out/8aB3G2A4b32-pc.txt $W $SB3 cuda "$PTC_DRY_EXTRA" "$PROF_PAIR_TRAIN_EXTRA" $RES/pair/a4 $RES/pair/a32 $J/state/cmd.i4_a4.sh $J/state/cmd.i4_a32.sh) > $J/out/mkcmd_pair.log 2>&1; then
    tail -n 12 $J/out/mkcmd_pair.log | cut -c1-600; say "PROF-PAIR FAILED: the job commands could not be built from the queue lines: i4 is skipped"; PFAIL="$PFAIL i4-cmd"; return 0
  fi
  cut -c1-1800 $J/out/mkcmd_pair.log
  { echo "# B3G2 pair on this box: custom_io at $B3G2_SHA; every file below was sha256-checked"; cat $J/out/b3g2_pins.txt; echo; cat $J/out/mkcmd_pair.log; } > $PRAW/pair_setup.md
  say "PROF-PAIR code ok: $npin pinned files match, caps_b3g2.json copied to $W/b3-inputs, the two commands are built (local_runner's own parse_queue and command); accum 4 first (timeout $PROF_PAIR_A4_MIN min), then accum 32 ($PROF_PAIR_A32_MIN min), $PROF_PAIR_STEP updates each"
  pair_run a4 4 $PROF_PAIR_A4_MIN; r=$?
  [ $r = 2 ] || pair_run a32 32 $PROF_PAIR_A32_MIN
}
prof_b3ab() {   # PROF_PLAN=b3ab (POOL is set): the profiler and syncs at accum 4, the equivalence of the variants (mark 6), then the A/B bench; each stage non-fatal under its own timeout
  local B3 mm
  say "PROF PLAN b3ab: B3G2 at accum 4: profiler and syncs, abequiv (mark 6), abbench (PREREG-b3g2-speed-ab.md: A = accum 4; B = accum 8,16,2 and tf32, pad64, unfused, nosync; 3 interleaved rounds), then i4_b3g2_pair (src-b3g2, accum 4 then 32, $PROF_PAIR_STEP updates each); DPH=$DPH; no AT-1, no PTC stages; budget $PROF_MAXMIN min from the start of stage prof"
  if [ -f $S/custom_io/g8a/caps_b3g2.json ] && [ -f $S/custom_io/models/b3g2.py ]; then
    B3="--arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json"
    PSTEP_MIN=$PROF_B3P_MIN
    pstep i1_b3g2_profile b3g2_profile.json $B3 --sections breakdown,throughput,padding,syncs
    PSTEP_MIN=$PROF_ABE_MIN
    pstep i2_b3g2_abequiv b3g2_abequiv.json $B3 --sections abequiv
    grep -E -e 'abequiv|mark 6|mark6' $PRAW/i2_b3g2_abequiv.log 2>/dev/null | tail -n 24 | cut -c1-260
    [ -f $PRAW/b3g2_abequiv.md ] && { echo "--- b3g2_abequiv.md"; head -n 40 $PRAW/b3g2_abequiv.md | cut -c1-300; }
    PSTEP_MIN=$PROF_ABB_MIN; mm=$(awk "BEGIN{print int($PROF_ABB_MIN * 0.6)}")
    pstep i3_b3g2_abbench b3g2_abbench.json $B3 --sections abbench --ab-accums 8,16,2 --ab-variants tf32,pad64,unfused,nosync --ab-rounds 3 --ab-warmup 10 --ab-updates 40 --ab-max-min $mm --ab-partial $PRAW/b3g2_abbench.partial.json --ab-equiv-json $PRAW/b3g2_abequiv.json --dph $DPH
    grep -E -e 'abbench|MARK|mark [0-9]|USD|usd|dph' $PRAW/i3_b3g2_abbench.log 2>/dev/null | tail -n 40 | cut -c1-300
    [ -f $PRAW/b3g2_abbench.md ] && { echo "--- b3g2_abbench.md"; head -n 80 $PRAW/b3g2_abbench.md | cut -c1-300; }
    PSTEP_MIN=
  else
    say "PROF B3G2 runs not made: $S/custom_io/g8a/caps_b3g2.json or $S/custom_io/models/b3g2.py is missing in the assembled tree"; PFAIL="$PFAIL b3g2-files-missing"
  fi
  prof_b3g2_pair      # i4_b3g2_pair: LAST, after i1, i2 and i3 (its own code, src-b3g2; skipped when PROF_PAIR_NEED_MIN minutes of the budget are not left)
  awk -v up=$(( $(date +%s) - T0 )) -v dph=$DPH -v maxh=$MAXH 'BEGIN{printf "PROF COST DPH=%s USD/h: up %.1f min = %.2f USD so far; MAXH %s h ceiling = %.2f USD (the rental, from DPH x time, not a bill)\n", dph, up/60, up/3600*dph, maxh, maxh*dph}'
}
prof_main() {   # never returns: ends with CIO DONE / CIO-FAIL and a sleep
  local rc jok t l PJ0 PJ1 BL EL PC B3 d alt
  stage prof; PT0=$(date +%s)
  say "PROF START job smoke of $PROF_JOB_STEPS updates, then the harness (commit $PROF_SHA); budget $PROF_MAXMIN min, maxh $MAXH h, speed guard OFF, up $(( (PT0 - T0) / 60 )) min so far"
  [ "$PROF_PLAN" = b3ab ] && say "PROF PLAN b3ab (PROF_PLAN): pool-building smoke of $PROF_JOB_STEPS updates, then ONLY the profiler and syncs at accum 4, abequiv and abbench, then i4_b3g2_pair (accum 4 and accum 32, $PROF_PAIR_STEP updates each, src-b3g2); maxh $MAXH h, budget $PROF_MAXMIN min, DPH $DPH"
  [ "$PROF_PLAN" = b3sweep ] && say "PROF PLAN b3sweep (PROF_PLAN): pool-building smoke of $PROF_JOB_STEPS updates, then ONLY the B3G2 accum sweep, the K-pinned comparison and two AT-1 speed runs; maxh $MAXH h, budget $PROF_MAXMIN min"
  mkdir -p $PRAW $OP
  fetch_sha $J/prof $PROF_SHA $PROF_DIR || die fetch-prof
  [ "$(sha $PY)" = "$PROF_PY_SHA" ] || die "prof_train.py is not the pinned one (got $(sha $PY))"
  say "PROF-HARNESS commit $PROF_SHA; prof_train.py sha256 $(sha $PY) = the pinned value; test_prof.py $(sha $J/prof/$PROF_DIR/prof/test_prof.py); README.md $(sha $J/prof/$PROF_DIR/prof/README.md); PREREG-eg-once.md $(sha $J/prof/$PROF_DIR/PREREG-eg-once.md)"
  . $J/state/env.sh          # local_runner's child_env, as the job gets it (PYTORCH_CUDA_ALLOC_CONF, OMP_NUM_THREADS=2 ...)
  if [ "$PTC_DRY" != 1 ]; then
    l=$(cat $J/state/cmd.job.mem); t=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    [ "${t:-0}" -ge "$l" ] || die "gpu memory free ${t:-?} MiB < $l (the queue's MEM line)"
  fi
  # the job smoke: cmd.job.txt (local_runner's own command) with --out in profjob and --steps / --train-extra appended (the last --train-extra wins in argparse; job.py: --steps is for dry runs)
  cat > $J/profcmd.py <<'PY'
import shlex, sys
src, dst, code, out, steps, extra = sys.argv[1:7]
t = shlex.split(open(src).read())
assert t.count('--out') == 1, t
t[t.index('--out') + 1] = out
t += ['--steps', steps, '--train-extra', extra]
line = ' '.join(shlex.quote(x) for x in t)
open(dst, 'w').write('#!/bin/bash\ncd %s || exit 1\nexec %s\n' % (shlex.quote(code), line))
print('PROF-JOB cmd:', line)
PY
  python $J/profcmd.py $J/state/cmd.job.txt $J/state/cmd.prof.sh $CODE $OP $PROF_JOB_STEPS "$PROF_JOB_TRAIN_EXTRA" > $J/out/profcmd.log 2>&1 || { cat $J/out/profcmd.log; die profcmd; }
  cut -c1-1800 $J/out/profcmd.log; cp $J/state/cmd.prof.sh $OP/cmd.prof.sh.txt
  cat > $J/profjob_report.py <<'PY'
import json, os, sys
op, j0, j1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
def load(p):
    try:
        return json.load(open(os.path.join(op, p)))
    except Exception:
        return {}
def mt(p):
    try:
        return os.path.getmtime(os.path.join(op, p))
    except OSError:
        return None
res, box, man = load('PTC/RESULT.json'), load('box.json'), load('pool_MANIFEST.json')
arm = (box.get('arms') or {}).get('PTC') or {}
ev = []
try:
    for ln in open(os.path.join(op, 'PTC', 'stdout.txt'), errors='replace'):
        if '"event": "train"' in ln:
            try:
                ev.append(json.loads(ln[ln.index('{'):]))
            except ValueError:
                pass
except OSError:
    pass
for e in ev:
    print('PROF-JOB train step=%s loss=%s lr=%s elapsed_s=%s cap_hits=%s' % (e.get('step'), e.get('loss'), e.get('lr'), e.get('elapsed'), e.get('cap_hits')))
steps, train_s = res.get('steps'), res.get('train_s')
d = dict(steps=steps, train_s=round(train_s, 1) if train_s else None, steps_per_s_result=res.get('steps_per_s'))
spu = None
if train_s and steps:
    spu = d['sec_per_update_overall'] = round(train_s / steps, 4)
if len(ev) >= 2 and ev[-1].get('step', 0) > ev[0].get('step', 0):
    spu = d['sec_per_update_first_to_last_log'] = round((ev[-1]['elapsed'] - ev[0]['elapsed']) / (ev[-1]['step'] - ev[0]['step']), 4)
    d['first_log_step'], d['last_log_step'] = ev[0]['step'], ev[-1]['step']
d['job_wall_s'] = round(j1 - j0, 1)
d['pool_build_s'] = box.get('pool_build_s')
d['arm_wall_s'] = arm.get('wall_s')
ck, rj, st = mt('PTC/checkpoint.pt'), mt('PTC/RESULT.json'), box.get('started_unix')
ev_s = round(rj - ck, 1) if ck and rj else None
d['final_eval_phase_s'] = ev_s              # RESULT.json's last write minus checkpoint.pt's write: final eval, chain-5, lesions (the checkpoint is saved right after training)
if ck and st and train_s and box.get('pool_build_s') is not None:
    d['startup_before_train_s'] = round(ck - train_s - (st + box['pool_build_s']), 1)       # arm process start to first update: imports, reading train.jsonl, vocab, model build
d['peak_mem_mib'], d['peak_reserved_mib'] = res.get('peak_mem_mib'), res.get('peak_reserved_mib')
print('PROF-JOB timing', json.dumps(d))
if spu:
    print('PROF-JOB projection for the 24,000-update job (this speed, suggested): train_h=%.2f final_eval_h=%s (the guard\'s EXTRA_H default is 0.5)' % (24000 * spu / 3600, round(ev_s / 3600, 3) if ev_s else None))
sch = man.get('schedule') or {}
print('PROF-JOB pool', json.dumps(dict(train_sha256=man.get('train_sha256'), train_bytes=man.get('train_bytes'), rows=man.get('rows'), pieces=round(man['pieces']) if man.get('pieces') else None, schedule_steps=sch.get('steps'), passes=sch.get('passes'))))
PY
  stage prof-job; TLOG=$OP/PTC/stdout.txt
  l=$(prof_left); t=$((PROF_JOB_MIN * 60)); [ $t -gt $l ] && t=$l; [ $t -lt 300 ] && t=300
  PJ0=$(date +%s)
  say "PROF-JOB START: the queue-built job command, --steps $PROF_JOB_STEPS, --train-extra '$PROF_JOB_TRAIN_EXTRA', out $OP; timeout $t s (budget left $l s)"
  runp $OP/stdout.txt $CODE timeout -k 30 $t bash $J/state/cmd.prof.sh; rc=$?
  PJ1=$(date +%s)
  say "PROF-JOB END rc=$rc secs=$((PJ1 - PJ0))$([ $rc = 124 ] && echo ' TIMEOUT') maxh_hit=$([ -e $J/state/maxh ] && echo yes || echo no)"
  tail -n 3 $OP/stdout.txt | cut -c1-300
  summary $OP; jok=$?
  python $J/profjob_report.py $OP $PJ0 $PJ1 2>&1 | cut -c1-700
  echo "job $rc $((PJ1 - PJ0)) $t" >> $J/state/prof_steps.txt
  { [ $rc = 0 ] && [ $jok = 0 ]; } || PFAIL="$PFAIL job(rc$rc,ok$jok)"
  # the harness on the pool the job smoke built
  POOL=$W/g8a/pools/p10-rung30-s400-a64-L
  if [ ! -f $POOL/train.jsonl ]; then
    alt=$(for d in $W/g8a/pools/*/; do [ -f ${d}train.jsonl ] && echo ${d%/}; done)
    if [ "$(echo "$alt" | grep -c .)" = 1 ]; then say "PROF WARN pool p10-rung30-s400-a64-L has no train.jsonl; using the only pool that has one: $alt"; POOL=$alt; else POOL=; fi
  fi
  if [ -z "$POOL" ]; then
    say "PROF no pool with a train.jsonl under $W/g8a/pools: no harness run"; PFAIL="$PFAIL no-pool"
  else
    say "PROF harness pool $POOL ($(stat -c %s $POOL/train.jsonl) bytes), --pkg-root $S, CUSTOM_IO_EG2=${CUSTOM_IO_EG2:-unset}"
    if [ "$PROF_PLAN" = b3ab ]; then prof_b3ab; elif [ "$PROF_PLAN" = b3sweep ]; then prof_b3sweep; else
    PC="--arm PTC --rung 3M --accum 16 --data $POOL --pkg-root $S"
    BL="baseline;eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;eg_once,sortpad,bigmb,oldw,prefetch;tf32"; [ "$PROF_COMPILE" = 1 ] && BL="$BL;eg_once,sortpad,oldw,compile"
    EL="eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;sortpad;bigmb;tf32;prefetch"
    pstep a_profile profile.json $PC
    pstep b_bench bench.json $PC --sections bench --updates 100 --warmup 20 --bench-rounds 2 --bench-list "$BL"
    pstep c_equiv equiv_gpu.json $PC --sections equiv --equiv-check --curve-updates 0 --equiv-list "$EL"
    pstep d_e4 equiv_e4.json $PC --sections equiv --equiv-check --curve-updates 300 --equiv-list eg_once
    if [ -f $S/custom_io/g8a/caps_b3g2.json ] && [ -f $S/custom_io/models/b3g2.py ]; then
      B3="--arm B3G2 --rung 3M --accum 32 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json"
      pstep f1_b3g2_profile b3g2_profile.json $B3 --sections breakdown,throughput,padding,syncs
      pstep f2_b3g2_bench b3g2_bench.json $B3 --sections bench --updates 40 --warmup 10 --bench-list "baseline;eg_once"
    else
      say "PROF B3G2 runs not made: $S/custom_io/g8a/caps_b3g2.json or $S/custom_io/models/b3g2.py is missing in the assembled tree"; PFAIL="$PFAIL b3g2-files-missing"
    fi
    fi
  fi
  stage result
  kill $WATCH 2>/dev/null; WATCH=
  prof_emit
  say "PROF-STEPS (name rc seconds timeout_s):"; cat $J/state/prof_steps.txt
  if [ -z "$PFAIL" ] && [ ! -e $J/state/maxh ]; then
    say "PROF DONE failed=none skipped=[$PSKIP] up_min=$(( ($(date +%s) - T0) / 60 ))"
    say "CIO DONE"; sleep $END_SLEEP; exit 0
  fi
  stage failed
  say "PROF DONE failed=[$PFAIL] skipped=[$PSKIP] maxh_hit=$([ -e $J/state/maxh ] && echo yes || echo no) up_min=$(( ($(date +%s) - T0) / 60 ))"
  say "CIO-FAIL PROFILE: a step failed or MAXH was reached (the results above are what exists). Collect them, then destroy the box"
  sleep $FAIL_SLEEP; exit 1
}

# ---- 1. box + packages
say "CIO START"; stage setup
say "PTC3S START job=$RUN maxh=$MAXH dph=$DPH guard=$(if [ "$PROFILE" = 1 ]; then echo OFF-profile-mode; elif [ "$DPH" != 0 ]; then echo on; else echo OFF-set-DPH; fi) cap_usd=$PROJ_CAP_USD tf=$TFVER eg=$EG dry=$PTC_DRY base=$BASE_SHA overlay=$OVL_SHA"
[ "$EG" = 1 ] || die "EG=1 is required: the job has eg_embed"
case $PROFILE in 0|1) ;; *) FAIL_SLEEP=120; die "PROFILE must be 0 or 1 (got '$PROFILE')";; esac
case $PROF_PLAN in default) ;; b3sweep|b3ab) [ "$PROFILE" = 1 ] || { FAIL_SLEEP=120; die "PROF_PLAN=$PROF_PLAN needs PROFILE=1"; };; *) FAIL_SLEEP=120; die "PROF_PLAN must be default, b3sweep or b3ab (got '$PROF_PLAN')";; esac
if [ "$PROFILE" = 1 ]; then
  say "PROF MODE: the GPU shake-out and profiling rental, not the job: stage prof replaces stage train (PROF_MAXMIN=$PROF_MAXMIN PROF_JOB_STEPS=$PROF_JOB_STEPS PROF_COMPILE=$PROF_COMPILE end_sleep=$END_SLEEP$([ "$PROF_PLAN" != default ] && echo " PROF_PLAN=$PROF_PLAN"))"
  [ -z "$PROF_DRY_ARGS$PROF_DRY_FAIL$PROF_DRY_HANG" ] || [ "$PTC_DRY" = 1 ] || die "PROF_DRY_* are CPU dry-run hooks and need PTC_DRY=1; never set them on Vast"
  if [ "$PTC_DRY" = 1 ] && command -v nvidia-smi >/dev/null && nvidia-smi -L 2>/dev/null | grep -q GPU; then die "PROFILE=1 with PTC_DRY=1 on a box that has a GPU: PTC_DRY is for the CPU dry run only"; fi
fi
if [ "$DPH" != 0 ] && [ "$MAXH" != 0 ] && awk "BEGIN{exit !($MAXH * $DPH > $PROJ_CAP_USD + 0.5)}"; then say "WARN MAXH x DPH = $(awk "BEGIN{print $MAXH * $DPH}") USD is above the cap $PROJ_CAP_USD USD plus 0.5: lower MAXH"; fi
[ "$PTC_DRY" = 1 ] || nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
free -g | head -2; nproc; df -h $J | tail -1
[ "$PTC_DRY" = 1 ] || [ "$(df -m $J | awk 'NR==2{print $4}')" -ge 20000 ] || die "less than 20 GB free disk on $J (the run needs about 15 GB)"
command -v git >/dev/null || (apt-get update -qq && apt-get install -y -qq git >/dev/null) || die git
git config --global core.autocrlf false
write_guard
watch_loop & WATCH=$!
PIP_BREAK_SYSTEM_PACKAGES=1 retry 3 pip install -q --break-system-packages "transformers==$TFVER" "safetensors==0.8.0" "tokenizers==0.23.2" accelerate numpy pyarrow huggingface_hub > $J/out/pip.log 2>&1 || { tail -3 $J/out/pip.log; die pip; }
python - $TFVER <<'PY' > $J/out/versions.txt 2>&1 || { cat $J/out/versions.txt; die versions; }
import importlib.metadata as m, sys
want = {'transformers': sys.argv[1], 'safetensors': '0.8.0', 'tokenizers': '0.23.2'}     # the PC's: transformers 5.19.0, tokenizers 0.23.2, safetensors 0.8.0
got = {k: m.version(k) for k in ('transformers', 'safetensors', 'tokenizers', 'huggingface_hub', 'numpy', 'pyarrow', 'accelerate')}
import torch
got['torch'] = torch.__version__ + ' cuda ' + str(torch.version.cuda)
print('versions', got)
bad = {k: (got[k], v) for k, v in want.items() if got[k] != v}
assert not bad, 'version mismatch (got, want): %s' % bad
PY
cat $J/out/versions.txt
if [ "$PTC_DRY" != 1 ]; then python -c "import torch; assert torch.cuda.is_available(), 'no cuda'; print('gpu', torch.cuda.get_device_name(0), 'bf16', torch.cuda.is_bf16_supported())" || die torch-cuda; fi
if [ "$PROFILE" = 1 ]; then      # the environment record for the PC-vs-box comparison (GPU, driver, torch, CUDA, packages, CPU), early in the log and in the profrun block
  { echo "# date $(date -u +%FT%TZ)"; echo "# uname"; uname -a; echo "# python"; python --version; echo "# nvidia-smi"; nvidia-smi 2>&1
    echo "# nvidia-smi gpu csv"; nvidia-smi --query-gpu=name,driver_version,memory.total,clocks.max.sm,clocks.max.mem,power.limit,pstate --format=csv 2>&1
    echo '# pip list | grep -i -E "torch|transformers|numpy" (and the other pinned packages)'; pip list 2>/dev/null | grep -i -E "torch|transformers|numpy|safetensors|tokenizers|triton|pyarrow|accelerate|huggingface|nvidia-"
    echo "# torch"; python -c '
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "cudnn", torch.backends.cudnn.version(), "cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print("gpu", p.name, "capability %d.%d" % (p.major, p.minor), "mem_GiB", round(p.total_memory / 2**30, 2), "sm_count", p.multi_processor_count, "bf16", torch.cuda.is_bf16_supported())
print("tf32 matmul", torch.backends.cuda.matmul.allow_tf32, "tf32 cudnn", torch.backends.cudnn.allow_tf32, "float32_matmul_precision", torch.get_float32_matmul_precision())
' 2>&1
    echo "# cpu"; lscpu | grep -E '^(Model name|CPU\(s\)|Thread|Core|Socket|CPU max MHz|CPU MHz)'; free -m | head -2; df -h $J | tail -1; } > $J/out/prof_env.txt 2>&1
  cut -c1-250 $J/out/prof_env.txt
fi
export HF_HUB_DISABLE_PROGRESS_BARS=1 TRANSFORMERS_VERBOSITY=error TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 PYTHONUTF8=1
stop_after setup

# ---- 2. code: base commit, PTC package, every hash checked as install_ptc.ps1 does, ptccheck on the CPU, a frozen copy as local_runner makes
stage code
fetch_sha $J/base $BASE_SHA custom_io || die fetch-base
fetch_sha $J/ovl $OVL_SHA $OVL_DIR || die fetch-overlay
# the package files (README.md tables and install_ptc.ps1): sha256 of the file here
while read -r f h; do [ "$(sha $OV/$f)" = "$h" ] || die "package file $f is not the pinned one (got $(sha $OV/$f))"; done <<'PKG'
@@PKG_PINS@@
PKG
# the six files PTC replaces: file here, path under custom_io, sha256 at 74d6e92c75 (- = none, a new file), sha256 of the PTC file
while read -r f dest old new; do
  [ "$(sha $OV/$f)" = "$new" ] || die "$f here is not the PTC file (got $(sha $OV/$f))"
  [ "$old" = - ] || [ "$(sha $B/$dest)" = "$old" ] || die "$dest in the base commit is not 74d6e92c75's (got $(sha $B/$dest))"
  for h in $new $old; do [ "$h" = - ] && continue; grep -qi $h $OV/README.md || die "README.md does not list $h"; grep -qi $h $OV/install_ptc.ps1 || die "install_ptc.ps1 does not list $h"; done
done <<'OVERLAYS'
@@OVERLAY_PINS@@
OVERLAYS
[ "$(sha $B/g8a/caps.py)" = "$CAPS_PY_SHA" ] || die "base g8a/caps.py is not 74d6e92c75's (got $(sha $B/g8a/caps.py))"
[ "$(sha $B/g8a/caps_b3s.json)" = "$CAPS_B3S_SHA" ] || die "base g8a/caps_b3s.json is not 74d6e92c75's (got $(sha $B/g8a/caps_b3s.json))"
grep -qi $CAPS_PY_SHA $OV/install_ptc.ps1 || die "install_ptc.ps1 does not list the caps.py hash"
# src-ptc = a copy of the base custom_io, checked again, then the six overlay files, checked again, then the two queue files
rm -rf $S; mkdir -p $S; cp -a $B $S/custom_io || die copy-base
[ "$(sha $S/custom_io/g8a/caps.py)" = "$CAPS_PY_SHA" ] || die "the copy of caps.py differs"
# PTC-SETUP-OK.txt in the format install_ptc.ps1 writes on the PC (upper-case hashes, backslash paths), so the two markers can be diffed
{ echo "caps.py ${CAPS_PY_SHA^^} (src-b3g2's, unchanged)"; echo "base: src-b3g2 = custom_io at 74d6e92c75"; } > $S/PTC-SETUP-OK.txt
while read -r f dest old new; do
  [ "$old" = - ] || [ "$(sha $S/custom_io/$dest)" = "$old" ] || die "the copy of $dest differs from the base"
  cp $OV/$f $S/custom_io/$dest || die "cannot copy $f"
  [ "$(sha $S/custom_io/$dest)" = "$new" ] || die "$f did not copy to $dest"
  if [ "$old" = - ]; then echo "${dest//\//\\} ${new^^} (new)" >> $S/PTC-SETUP-OK.txt; else echo "${dest//\//\\} ${new^^} (was ${old^^})" >> $S/PTC-SETUP-OK.txt; fi
done <<'OVERLAYS'
@@OVERLAY_PINS@@
OVERLAYS
mkdir -p $S/custom_io/queue_local
for q in 8aPTC3S 8aPTC10S; do cp $OV/$q-pc.txt $S/custom_io/queue_local/$q-pc.txt; cmp -s $OV/$q-pc.txt $S/custom_io/queue_local/$q-pc.txt || die "$q-pc.txt did not copy"; done
say "src-ptc: base files and caps.py are 74d6e92c75's, the 6 PTC files and 2 queue files are in, all sha256 ok"
say "ptccheck on the CPU (about 2 minutes)"
for k in 1 2; do     # the check is deterministic, but one failure in about ten CPU runs was seen on the dry-run box (cause not found): one more try, and on a second failure the whole test output
  runp $J/out/ptccheck.log $S env CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python $OV/ptccheck.py $J/base
  rc=$?; tail -n 6 $J/out/ptccheck.log | cut -c1-300
  { [ $rc = 0 ] && tail -n 1 $J/out/ptccheck.log | grep -q 'PTC CPU CHECK OK'; } && break
  [ -e $J/state/maxh ] && die maxh
  if [ $k = 2 ]; then
    (cd $S && CUDA_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$S PTC_ORIG_TREE=$J/base python -m custom_io.tests.test_ptc 2>&1 | tail -n 40 | cut -c1-300; df -m $J /tmp | cat)
    die "ptccheck failed twice (rc $rc)"
  fi
  say "ptccheck try 1 failed (rc $rc), trying once more; disk: $(df -m $J /tmp | awk 'NR>1{printf "%s MB free on %s; ", $4, $6}')"
done
echo "queues 8aPTC3S and 8aPTC10S in custom_io\\queue_local; ptccheck ok (CPU); ptc3s_box.sh (Linux box, not install_ptc.ps1)" >> $S/PTC-SETUP-OK.txt
# the frozen copy local_runner makes (WORK/code/QUEUE-HASH, no results/, __pycache__, *.pt) and its hash: compare with the PC log's `code:` line
CODE_H=$(cd $S && python -c "from custom_io.local_runner import code_hash; print(code_hash())") || die code-hash
CODE=$W/code/$QNAME-$CODE_H
rm -rf $CODE; mkdir -p $CODE; (cd $S && tar -c --exclude=results --exclude=__pycache__ --exclude='*.pt' custom_io | tar -x -C $CODE) || die freeze
(cd $CODE && find custom_io -type f \( -name '*.py' -o -name '*.json' -o -name '*.txt' \) | sort | xargs sha256sum) > $J/out/code_files.sha256
# code_identity.py (the same file is in the kit folder; the PC runs it on WORK\code\8aPTC3S-pc-<hash>): sha256 of every .py/.json/.txt file with CRLF turned into LF, and a code hash that does not depend on line endings or on how the OS sorts paths
cat > $J/code_identity.py <<'PYID'
@@CODE_IDENTITY_PY@@
PYID
python -I $J/code_identity.py $CODE files > $J/out/code_files_lf.sha256 && python -I $J/code_identity.py $CODE hash > $J/out/code_hash_lf.txt && python -I $J/code_identity.py $CODE > $J/out/code_identity.txt || die code-identity
say "CODE-ID $QNAME-$CODE_H (PC: WORK\\code\\$QNAME-<same 10 hex>); code_identity.py (CRLF as LF): $(tr "\n" " " < $J/out/code_identity.txt); raw-bytes file list sha256 $(sha $J/out/code_files.sha256); caps.py $CAPS_PY_SHA"
# the two job lines as local_runner would run them (its parse_queue and command), plus its child environment
cat > $J/mkcmd.py <<'PY'
import json, os, shlex, sys
from pathlib import Path
from custom_io.local_runner import parse_queue, command, child_env, queue_env
queue, work, outroot, code, device, extra = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]), sys.argv[4], sys.argv[5], json.loads(sys.argv[6])
runs = parse_queue(queue, work)
assert [(r[0], r[1]) for r in runs] == [('8a-data', 'g8a-data'), ('8aPTC3S-3M-s400', 'g8a')], [(r[0], r[1]) for r in runs]
state = Path(os.environ['J']) / 'state'
for (name, kind, args, mem), fn in zip(runs, ('cmd.data', 'cmd.job')):
    out = outroot / name
    line = ' '.join(shlex.quote(c) for c in command(kind, args + (extra if kind == 'g8a' else []), work, out, device))
    (state / (fn + '.sh')).write_text('#!/bin/bash\ncd %s || exit 1\nexec %s\n' % (shlex.quote(code), line))
    (state / (fn + '.txt')).write_text(line + '\n')                      # what the runner writes as cmd.txt
    (state / (fn + '.mem')).write_text('%d\n' % mem)
    print('CMD', name, 'mem', mem, 'MiB:', line)
env = child_env(device)
(state / 'env.sh').write_text(''.join('export %s=%s\n' % (k, shlex.quote(v)) for k, v in sorted(env.items()) if os.environ.get(k) != v))
print('CHILD-ENV (added to the environment):', {k: v for k, v in sorted(env.items()) if os.environ.get(k) != v})
print('QUEUE-ENV (the PC\'s # ENV lines, Windows paths, not used here):', json.dumps(queue_env(queue)))
PY
# (the commands are always built for cuda: local_runner's command() adds --device cpu to EVERY line kind on cpu, which get_data rejects; the dry run gets --device cpu through PTC_DRY_EXTRA)
(cd $CODE && export J PYTHONPATH=$CODE && python $J/mkcmd.py $CODE/custom_io/queue_local/8aPTC3S-pc.txt $W $RES $CODE cuda "$PTC_DRY_EXTRA") > $J/out/mkcmd.log 2>&1 || { cat $J/out/mkcmd.log; die mkcmd; }
cut -c1-1500 $J/out/mkcmd.log
stop_after code

# ---- 3. EmbeddingGemma 2 (frozen), pinned revision, anonymous download with box.sh's retry loop, then its 3-vector check
stage gemma
if [ "$PTC_DRY" != 1 ] || [ "$PTC_DRY_EG" = 1 ]; then
  for k in 1 2 3 4 5 6; do   # anonymous Hugging Face downloads are rate limited per IP (a shared box IP can be out of requests): wait and retry
    runp $J/out/eg_dl.log $S python -c "from huggingface_hub import snapshot_download as s; from custom_io.models.eg import EG_ID, EG_REV; s(EG_ID, revision=EG_REV, local_dir='$J/eg2')" && break
    tail -2 $J/out/eg_dl.log; [ -e $J/state/maxh ] && die maxh; [ $k = 6 ] && die eg-download; say "eg download try $k failed, retrying in 4 min"; sleep 240
  done
  [ "$(sha $J/eg2/model.safetensors)" = "$EG2_ST_SHA" ] || die "EmbeddingGemma model.safetensors sha256 is $(sha $J/eg2/model.safetensors), not $EG2_ST_SHA"
  export CUSTOM_IO_EG2=$J/eg2
  EGDEV=cuda; [ "$PTC_DRY" = 1 ] && EGDEV=cpu
  runp $J/out/eg_check.log $CODE python -m custom_io.models.eg check $EGDEV; rc=$?; tail -n 4 $J/out/eg_check.log | cut -c1-400
  [ $rc = 0 ] || die eg-check
fi
stop_after gemma

# ---- 4. the PC's inputs under WORK/8a-inputs and WORK/b3-inputs, then its g8a-data line (get_data: own text, FineWeb-Edu shard 0, web slices hash-checked)
stage data
fetch_sha $W/8a-inputs/data-pool $DP_SHA data_pool/built data_pool/panels || die fetch-data-pool
fetch_sha $W/8a-inputs/own-data $OWN_SHA || die fetch-own-data
mkdir -p $W/b3-inputs; cp $W/8a-inputs/data-pool/data_pool/cloze_long.py $W/b3-inputs/cloze_long.py; cp $S/custom_io/g8a/caps_b3s.json $W/b3-inputs/caps_b3s.json
[ "$(sha $W/b3-inputs/cloze_long.py)" = "$CLOZE_SHA" ] || die "cloze_long.py is not the pinned one (got $(sha $W/b3-inputs/cloze_long.py))"
[ "$(sha $W/b3-inputs/caps_b3s.json)" = "$CAPS_B3S_SHA" ] || die "caps_b3s.json is not the pinned one"
[ "$(sha $W/8a-inputs/data-pool/data_pool/built/own72_MANIFEST.json)" = "$MANIFEST_SHA" ] || die own72-manifest
say "data branches fetched at $DP_SHA and $OWN_SHA; building the 8a data (FineWeb-Edu shard 0 is 2.15 GB; the slices must hash to the manifest)"
mkdir -p $RES/8a-data
for k in 1 2 3; do
  runp $J/out/get_data.log $CODE bash $J/state/cmd.data.sh && break
  tail -n 8 $J/out/get_data.log | cut -c1-400; [ -e $J/state/maxh ] && die maxh; [ $k = 3 ] && die get_data; say "get_data try $k failed, retrying in 3 min (it resumes)"; sleep 180
done
tail -n 3 $J/out/get_data.log | cut -c1-300
[ -f $W/data8a/READY.json ] && [ ! -f $W/data8a/REFUSED.txt ] || die "data8a not ready"
stop_after data

# ---- 5. the skills curriculum, as box.sh (200k seed-1 build, dev 40 per cell, hashes against FULL-BUILD-MANIFEST-200k-seed1.json; then the dev-200 build with the same train.jsonl)
stage skills
fetch_sha $J/cur $CUR_SHA skills_curriculum || die clone-cur
runp $J/out/build.log $J/cur python -m skills_curriculum.build --out $D --train 200000 --dev-per-cell 40 --seed 1 || { tail -3 $J/out/build.log; die build; }
python -c "import json; a=json.load(open('$J/cur/skills_curriculum/FULL-BUILD-MANIFEST-200k-seed1.json'))['files_sha256']; b=json.load(open('$D/manifest.json'))['files_sha256']; assert a==b, 'curriculum hash mismatch'; print('curriculum hashes match')" || die hash
runp $J/out/build_big.log $J/cur python -m skills_curriculum.build --out $DB --train 200000 --dev-per-cell 200 --seed 1 || { tail -3 $J/out/build_big.log; die build-big; }
[ "$(sha $D/train.jsonl)" = "$(sha $DB/train.jsonl)" ] || die big-train-hash
echo "big build train.jsonl hash matches"
stop_after skills
[ "$PROFILE" = 1 ] && prof_main      # PROFILE=1: stage prof instead of stage train; it never returns

# ---- 6. the job: the queue file's g8a line with local_runner's own prefix (--work WORK/g8a --local --out OUT --skills WORK/data --big-data WORK/data_big --data8a WORK/data8a)
stage train
if [ "$PTC_DRY" != 1 ]; then
  need=$(cat $J/state/cmd.job.mem); free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
  [ "${free:-0}" -ge "$need" ] || die "gpu memory free ${free:-?} MiB < $need (the queue's MEM line)"
fi
. $J/state/env.sh              # local_runner's child_env: PYTHONUNBUFFERED, PYTHONUTF8, OMP_NUM_THREADS=2, TOKENIZERS_PARALLELISM, HF_HUB_DISABLE_PROGRESS_BARS, TRANSFORMERS_VERBOSITY, PYTORCH_CUDA_ALLOC_CONF
mkdir -p $O; cp $J/state/cmd.job.txt $O/cmd.txt
say "PTC3S TRAIN START job=$RUN accum=PTC=16 seed=400 rung=3M expected_pool=p10-rung30-s400-a64-L code=$QNAME-$CODE_H"
runp $O/stdout.txt $CODE bash $J/state/cmd.job.sh; rc=$?
echo "rc=$rc" > $O/rc.txt
stage result
kill $WATCH 2>/dev/null; WATCH=
say "PTC3S JOB END rc=$rc maxh_hit=$([ -e $J/state/maxh ] && echo yes || echo no) guard_stop=$([ -e $J/state/guard_stop ] && echo yes || echo no)"
tail -n 3 $O/stdout.txt | cut -c1-300; ls -la $O/PTC 2>/dev/null | head -8
ls -d $W/g8a/pools/* 2>/dev/null | head;
boxfiles; summary; jobok=$?
emit $RUN $O
say "PTC3S RESULT PRINTED rc=$rc job_ok=$([ $jobok = 0 ] && echo yes || echo NO) (collect now; the checkpoint parts follow)"
stage export
[ "$EXPORT_CK" = 1 ] && ck_export
emit $RUN $O      # the result again, last, so a late collect still finds it in the 20,000-line window
if [ $rc = 0 ] && [ $jobok = 0 ]; then
  say "CIO DONE"
  sleep $END_SLEEP
else
  stage failed
  say "CIO-FAIL the job did not finish cleanly (rc=$rc; RESULT-SUMMARY above: job_status, arm_status, final_eval). Collect what was printed, then destroy the box"
  sleep $FAIL_SLEEP; exit 1
fi
