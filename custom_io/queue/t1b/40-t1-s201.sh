# MEM 6000
# PAR 1
# q40 T1 screen, T1_s201: the same line as custom_io/queue_local, code pinned to 68e2cd5f58 (the commit the PC chain would have used).
# Rented RTX 5090 (Ben's Vast OK, 3:00 PM ET 10-07: PC and Mac both busy). Data = the box's seed-1 200k build (train.jsonl sha256 010af671..., the same file as q33's).
# Box: python3 custom_io/box/vast.py create --offer ID --label cio-t1b --maxpar 2 --qsub /t1b --env "MAXH=12 IDLE_EXIT=5400 END_SLEEP=600 FAIL_SLEEP=1800"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SHA=68e2cd5f580321858eb671454b987df489517d10
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
run T1_s201 --model tool --cfg '{}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 201 --log-every 500 --final-eval --save-preds
