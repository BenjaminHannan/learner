# MEM 6000
# PAR 1
# q60 T1SD re-screen (MARKS-D0-T1-2026-10-07.md Amendment 7: T1SI + the distance-from-end table on the span keys), T1SD_s201: the same line as
# custom_io/queue_local/60-pc-t1sd-screen.txt (PASS-MARKS addendum 22 amendment 4), code pinned to 9ea8b6c0cb. Same recipe and data as
# T1/T1S/T1SI (the box's seed-1 200k build, hash-checked). Rented RTX 5090 (Ben's Vast OK; account auto-refills).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SHA=9ea8b6c0cb4bbda9c980261b3b9332ba395e0265
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
run T1SD_s201 --model tool --cfg '{"span_copy": true, "span_idx": true, "span_end": true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval --save-preds
