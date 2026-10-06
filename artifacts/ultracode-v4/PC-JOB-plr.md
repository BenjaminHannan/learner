# PC job: PLR (ultracode v4, low priority, for the Mac session to run on BensPC or the M1 Pro)

Run this only AFTER the door runs (`PC-JOB-pxw.md`, `PC-JOB-wd.md`) and the talker-calls-calculator runs (`PC-JOB-crt.md`, coming) have started; it must never delay them. Use free room on the 5070 Ti or the M1 Pro. Never rent Vast for it.

Branch `claude/ultracode-learning-blocker-gh011t`. Copy its `scripts/cap256_launch/uc_diag_v4.py` over the pipeline's copy in `<PIPE>/scripts/cap256_launch/` (superset; defaults unchanged; needs commit 87f252f52 or later for `--round-routers`).
Same `<PIPE>`, `<DATA>`, `<M2>` and data hash check as `PC-JOB-pxw.md`.
Each run peaks near 6 GB of GPU memory (no LM-feature cache beyond the screen's ~2,700 rows), so two or three fit next to each other on the 16 GB card when it is otherwise free; check `nvidia-smi` free memory before each start and keep at least 1.5 GB spare. Hold `C:\Users\benja\GPU-BUSY.txt` while any run is on the PC. No checkpoints written; output under 100 KB per run.

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
U=$P/scripts/cap256_launch/uc_diag_v4.py
COMMON="--mode plan --warmup 200 --fresh-core --op-attend --lr-cosine --screen-rows --round-routers --root $P --data $D --parent-path $M2"
# smoke (~2 min; 200 fresh chain rows instead of the screen rows, since --screen-rows always runs its full ~2,700 updates): must print RESULT lines
# plan-round-routers {"rounds": 4, "blocks": 2, "added_params": 16448, ...}, plan-eval, plan-round-experts, then DIAG-DONE plan
python $U ${COMMON/--screen-rows /} --fresh-rows 200 --sample-seed 1 --out $P/artifacts/uc/46-plr-smoke
# the six runs (seeds 1-6), as many at once as fit
for s in 1 2 3 4 5 6; do
  python $U $COMMON --sample-seed $s --out $P/artifacts/uc/46-plr-s$s > $P/artifacts/uc/46-plr-s$s.stdout.txt 2>&1
done
```
Results: push each run's `DIAG-plan.json` and stdout to `artifacts/ultracode-v4/results/46-plr-s<seed>/` on branch `claude/ultracode-learning-blocker-gh011t` (`git add -f`; artifacts/ is gitignored). Pass marks: `artifacts/ultracode-v4/DIAG-v4.md`, section "PLR", written before the runs (paired with PLS seeds 1-6).
