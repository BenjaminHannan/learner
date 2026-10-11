# GX stage 1 on one rented RTX 5090 (spec design/8a-gx-experts-2026-10-09.md addendum G): ONE seed, GX-3M and its G-B2 3M control trained side by
# side on this same box, same code, same data, same flags as the PC queues (accum 4 each). Called by custom_io/queue/gx{A,B}/*.sh inside box.sh
# (cwd = the job's frozen code copy; J, D, DB, JOB exported by box.sh; EG=1 gives CUSTOM_IO_EG2).
#   bash custom_io/box/gx_box.sh SEED CONTROL_QUEUE      e.g. 400 8aG1d  (analyze_gx reads 8aGX-3M-sSEED and CONTROL_QUEUE-3M-sSEED folders)
set -u
S=$1; C=$2; O=$J/w/$JOB; W=$J/g8a8; R=https://github.com/BenjaminHannan/learner
mkdir -p $O $W
say() { echo "=== $* $(date -u +%FT%TZ)"; }
say "GX box seed $S: inputs"
pip install -q --break-system-packages pyarrow > $O/pip_pyarrow.log 2>&1 || { tail -3 $O/pip_pyarrow.log; exit 1; }
if [ ! -d $J/dp ]; then
  git clone -q --depth 1 --filter=blob:none --sparse -b claude/data-pool-8b $R $J/dp && git -C $J/dp sparse-checkout set data_pool/built data_pool/panels || exit 1
fi
[ -d $J/od ] || git clone -q --depth 1 -b claude/8a-own-data $R $J/od || exit 1
python -m custom_io.g8a.get_data --work $W --data-pool $J/dp --own-xz $J/od --out $O/data8a-check \
  --expect-manifest-sha e8f32daf44d562910db6700bd73b64c720beb6e5c1c5a9a115e8c8880f0763b0 > $O/get_data.log 2>&1 || { tail -5 $O/get_data.log; exit 1; }
say "GX box seed $S: data ok, training GX and control"
COMMON="--rung 3M --seed $S --work $W/g8a --local --skills $D --big-data $DB --data8a $W/data8a --arms B2 --accum B2=4"
# one-level links so box.sh's TICK lines and its events files show each arm's training lines
mkdir -p $O/tick-gx $O/tick-ctl
ln -sf $O/8aGX-3M-s$S/B2/stdout.txt $O/tick-gx/stdout.txt
ln -sf $O/$C-3M-s$S/B2/stdout.txt $O/tick-ctl/stdout.txt
python -m custom_io.g8a.job $COMMON --out $O/8aGX-3M-s$S --b2-extra '{"eg_embed": true, "experts": 52, "top_k": 8}' > $O/job-gx.log 2>&1 &
p1=$!
python -m custom_io.g8a.job $COMMON --out $O/$C-3M-s$S --b2-extra '{"eg_embed": true}' > $O/job-ctl.log 2>&1 &
p2=$!
wait $p1; r1=$?
wait $p2; r2=$?
say "GX box seed $S: GX rc=$r1, control rc=$r2"
tail -3 $O/job-gx.log $O/job-ctl.log
[ $r1 = 0 ] && [ $r2 = 0 ]
