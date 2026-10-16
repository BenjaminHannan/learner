# LT-2 checkpoint export (sourced by lt2_box.sh; also by the CPU dry run in logic_transfer/box/dry_export.sh, so the dry run runs this very code).
# Needs: J (job root; run checkpoints are $J/w/ladder/rung<r>/<run>/checkpoint.pt), CKX (path of custom_io/box/ck_export.sh), say().
# lt2_export_loop <rung>: prints each run's FINAL checkpoint through ck_export.sh (3 MB parts in the log, one part per PACE seconds) as soon as that run has written it
# (course.py writes checkpoint.pt once, atomically, at the end of a run), so a finished run is not waiting for the slowest one; ends after rung<r>/DONE.json exists
# (written when every run of the rung has ended) and one last scan found nothing new. Each checkpoint gets its own block-label prefix (the collector keys blocks by label).
# Read the result with: vast.py collectck --id ID --out DIR --want "rung<r>/<run> ..."   (--want, because every checkpoint is its own ck_export call with its own CKDONE).
lt2_export_loop() {
  r=$1; n=0; seen=" "; fin=0
  while true; do
    for c in $J/w/ladder/rung$r/*/checkpoint.pt; do
      [ -f "$c" ] || continue
      case "$seen" in *" $c "*) continue;; esac
      seen="$seen$c "; n=$((n + 1))
      say "EXPORT rung $r $(basename $(dirname $c)) ($n) start"
      ( export GLOB="$c" CKROOT=$J/w/ladder PFX=ck${r}x${n}x PACE=${CKPACE:-100} LOG=/dev/stdout CKLOCK=$J/res/emit.lock; . $CKX ); say "EXPORT rung $r $(basename $(dirname $c)) ($n) printed"
    done
    [ $fin = 1 ] && break
    [ -f $J/w/ladder/rung$r/DONE.json ] && fin=1 && continue   # one more scan after DONE.json, then stop
    sleep ${CKPOLL:-30}
  done
  say "EXPORT rung $r done ($n checkpoints)"
}
