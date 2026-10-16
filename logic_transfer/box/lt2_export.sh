# LT-2 checkpoint export (sourced by lt2_box.sh; also by the CPU dry run in logic_transfer/box/dry_export.sh, so the dry run runs this very code).
# Needs: J (job root; run checkpoints are $J/w/ladder/rung<r>/<run>/checkpoint.pt), CKX (path of custom_io/box/ck_export.sh), say().
# lt2_export_loop <rung>: prints each run's FINAL checkpoint through ck_export.sh (1 MB parts in the log, one part per CKPACE=40 s: the collector's newest-9000-lines window then
# holds about 3 parts, so one slow or missed poll is covered) as soon as that run has written it (course.py writes checkpoint.pt once, atomically, at the end of a run), so a
# finished run is not waiting for the slowest one. Ends after rung<r>/DONE.json exists (every run of the rung has ended), one last scan found nothing new, and a SECOND pass has
# printed every checkpoint again (CKPASSES=2; same bytes, ck_export reuses the tgz), so a part lost in pass 1 (a poll that missed its window) is recovered from pass 2. The
# operator destroys the box as soon as the collector has every checkpoint sha-matched, which normally ends pass 2 early. Each print has its own block-label prefix.
# Read the result with: vast.py collectck --id ID --out DIR --want "rung<r>/<run> ... lt2-rung<r>"   (--want, because every checkpoint is its own ck_export call with its own CKDONE).
lt2_export_one() {   # rung, pass, index, checkpoint path
  ( export GLOB="$4" CKROOT=$J/w/ladder PFX=ck$1p$2x$3x PACE=${CKPACE:-40} CKPART=${CKPART:-1000000} LOG=/dev/stdout CKLOCK=$J/res/emit.lock; . $CKX )
}
lt2_export_loop() {
  r=$1; n=0; seen=" "; fin=0; all=""
  while true; do
    for c in $J/w/ladder/rung$r/*/checkpoint.pt; do
      [ -f "$c" ] || continue
      case "$seen" in *" $c "*) continue;; esac
      seen="$seen$c "; n=$((n + 1)); all="$all $c"
      say "EXPORT rung $r $(basename $(dirname $c)) pass 1 ($n) start"
      lt2_export_one $r 1 $n $c
      say "EXPORT rung $r $(basename $(dirname $c)) pass 1 ($n) printed"
    done
    [ $fin = 1 ] && break
    [ -f $J/w/ladder/rung$r/DONE.json ] && fin=1 && continue   # one more scan after DONE.json, then stop
    sleep ${CKPOLL:-30}
  done
  pass=2
  while [ $pass -le ${CKPASSES:-2} ]; do
    k=0
    for c in $all; do
      k=$((k + 1)); say "EXPORT rung $r $(basename $(dirname $c)) pass $pass ($k) start"
      lt2_export_one $r $pass $k $c
    done
    pass=$((pass + 1))
  done
  say "EXPORT rung $r done ($n checkpoints, ${CKPASSES:-2} passes)"
}
