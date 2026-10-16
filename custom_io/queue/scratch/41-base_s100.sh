# MEM 6000
# PAR 1
# Scratch A/B screen (run card pre-registered by the coordinator, Oct 16): run 1 of 6, one at a time (box launched with
# MAXPAR=1, QSUB=/scratch, BR=claude/project-thread-2zeaoc). Training flags exactly as the card; then the readouts
# (custom_io/scratch_readout.py) on this run's own checkpoint. watch130.sh stops the run if training projects past 130 min.
run base_s100 --model register_loop --cfg '{}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --seed 100 --log-every 500 --final-eval --minutes 150 &
bash custom_io/box/watch130.sh base_s100 $! &
wait
[ -f $J/w/$JOB/base_s100/checkpoint.pt ] && [ ! -f $J/w/$JOB/base_s100/STOPPED.json ] && \
  python -m custom_io.scratch_readout --run $J/w/$JOB/base_s100 --data $D --big-data $DB --bf16 > $J/w/$JOB/base_s100/readout.stdout.txt 2>&1
echo "{\"event\": \"readout_rc\", \"rc\": $?}"
