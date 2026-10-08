# MEM 6000
# PAR 1
# q80 T1SDR 6-seed confirm (MARKS-D0-T1-2026-10-07.md Amendment 10 / Note 10a: seeds 202-205 of T1SDR as built, recipe unchanged), T1SDR_s205:
# the same line as custom_io/queue_local/80-pc-t1sdr-confirm.txt (PASS-MARKS addendum 22 amendment 6), code pinned to f6d724cffc (q70's pin). Same recipe and data as
# T1/T1S/T1SI/T1SD (the box's seed-1 200k build, hash-checked). Rented RTX 5090 (Ben's Vast OK; account auto-refills).
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
SHA=f6d724cffc86e028b4286cc17a2d022e78541f77
P=$J/pin/$JOB; rm -rf $P
git clone -q --depth 1 --filter=blob:none --no-checkout --sparse -b claude/custom-reader-talker-4x309r https://github.com/BenjaminHannan/learner $P \
  && git -C $P fetch -q --depth 1 --filter=blob:none origin $SHA && git -C $P sparse-checkout set custom_io && git -C $P checkout -q $SHA || { echo "PIN-FAIL $SHA"; exit 3; }
[ "$(git -C $P rev-parse HEAD)" = "$SHA" ] || { echo "PIN-FAIL head $(git -C $P rev-parse HEAD)"; exit 3; }
rm -rf $J/code/$JOB/custom_io && cp -r $P/custom_io $J/code/$JOB/ && echo "custom_io pinned to $SHA"
run T1SDR_s205 --model tool --cfg '{"span_copy": true, "span_idx": true, "span_end": true, "ans_drill": 0.25}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 205 --log-every 500 --final-eval --save-preds
