# MEM 6000
# PAR 1
# q53 T1SI re-screen (Amendment 5: T1S + the entry-index term on the span keys), T1SI_s201: the same line as custom_io/queue_local/53-pc-t1si-screen.txt (PASS-MARKS addendum 22 amendment 3),
# code pinned to e5389aa5e7. Same box, data and recipe as T1_s201 (queue 40): the box's seed-1 200k build (train.jsonl sha256 010af671..., q33's file).
# Rented RTX 5090 (Ben's Vast OK, 3:00 PM ET 10-07; account auto-refills).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SHA=e5389aa5e7da91d2f802a67514d689cb4545ac00
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
run T1SI_s201 --model tool --cfg '{"span_copy": true, "span_idx": true}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval --save-preds
