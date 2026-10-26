# MEM 3000
# PAR 1
# write_copy re-scored with the Amendment 4 scorer at Amendments 7/8's n >= 1000 per cell (--min-n 1000): T1SDR_s200 (queue 70), once its run has
# finished. Code pinned to f6d724cffc; same dev file, eval batch 128 and bf16 as train.py's final eval.
SHA=f6d724cffc86e028b4286cc17a2d022e78541f77
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
until [ -f $J/w/70-t1sdr-s200/T1SDR_s200/RESULT.json ] && grep -q '"status": "ok"' $J/w/70-t1sdr-s200/T1SDR_s200/RESULT.json; do [ -f $J/state/70-t1sdr-s200.done ] && { echo "T1SDR run ended without an ok RESULT"; exit 4; }; sleep 60; done
mkdir -p $J/w/$JOB/T1SDR_s200
python -m custom_io.rescore_wc --ck $J/w/70-t1sdr-s200/T1SDR_s200/checkpoint.pt --data $D --big-data $DB --out $J/w/$JOB/T1SDR_s200/WC.json --device cuda --bf16 --eval-batch 128 --min-n 1000 --max-passes 12
