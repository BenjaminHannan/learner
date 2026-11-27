# MEM 3000
# PAR 1
# write_copy re-scored with the Amendment 4 scorer (unambiguous copies only, >= 200 per length): T1S_s201 (queue 50), once its run has finished.
# Code pinned to 834eb6546a (Tool.write_copy_u, custom_io/rescore_wc.py); same dev file, eval batch 128 and bf16 as train.py's final eval.
SHA=834eb6546a8686679465f527b626bd7cf3fce29d
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
until [ -f $J/w/50-t1s-s201/T1S_s201/RESULT.json ] && grep -q '"status": "ok"' $J/w/50-t1s-s201/T1S_s201/RESULT.json; do [ -f $J/state/50-t1s-s201.done ] && { echo "T1S run ended without an ok RESULT"; exit 4; }; sleep 60; done
mkdir -p $J/w/$JOB/T1S_s201
python -m custom_io.rescore_wc --ck $J/w/50-t1s-s201/T1S_s201/checkpoint.pt --data $D --big-data $DB --out $J/w/$JOB/T1S_s201/WC.json --device cuda --bf16 --eval-batch 128
