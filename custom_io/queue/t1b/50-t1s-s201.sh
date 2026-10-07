# MEM 6000
# PAR 1
# q50 T1S re-screen, T1S_s201: the same line as custom_io/queue_local/50-pc-t1s-screen.txt (T1 + span copy, Amendment 3, PASS-MARKS addendum 22),
# code pinned to 1af99f63eb. Same box, data and recipe as T1_s201 (queue 40): the box's seed-1 200k build (train.jsonl sha256 010af671..., q33's file).
# Rented RTX 5090 (Ben's Vast OK, 3:00 PM ET 10-07; account auto-refills).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SHA=1af99f63eb4896206dffe9368737f9cf172d01b5
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
run T1S_s201 --model tool --cfg '{"span_copy": true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval --save-preds
