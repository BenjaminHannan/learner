# PC job: CRT (ultracode v4; the talker calls the calculator; for the Mac session, BensPC)

Same setup as `PC-JOB-pxw.md` (copy the branch's `scripts/cap256_launch/uc_diag_v4.py` and `skills_pretrain_v1.py` over the pipeline's copies; same `<PIPE>`, `<DATA>`, `<M2>`, data hash check, `GPU-BUSY.txt` marker shared with the custom reader/talker thread). Needs commit with `--plan-talk` (see `git log -- scripts/cap256_launch/skills_pretrain_v1.py`).
Each run: about 20 min planner pretraining (17,000 chain rows), then 6,000 updates and the lesion evals; about 9 GB peak. One at a time on the 16 GB card unless `nvidia-smi` shows 10 GB free next to another job; a second one can run on the M1 Pro.

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
S=$P/scripts/cap256_launch/skills_pretrain_v1.py
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
FIT="--families $W8 --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
COMMON="--root $P --data $D --parent-path $M2 --no-checkpoint --minutes 170 --copy-path --gen-fix $FIT --steps --steps-rich --seq-steps-v2 --plan-route 17000 --plan-cosine --plan-talk --final-lesions --save-texts"
# smoke (~5 min; first real-LM run of the new code). Must print: plan-pretrain-done, plan-talk-labels (A starts ' calc(', B ' = ', C ' # '),
# skills-eval with a "talk" block, final lesions including note_drop, then SKILLS-RESULT. Any Traceback: stop and report it with the last 40 lines.
python $S --root $P --data $D --parent-path $M2 --no-checkpoint --copy-path --gen-fix --families $W8 --fixed-rows 20 --passes 2 --updates 40 --eval-every 40 --dev-n 16 --sample-seed 9 --steps --steps-rich --seq-steps-v2 --plan-route 300 --plan-cosine --plan-talk --final-lesions --save-texts --out $P/artifacts/uc/47-crt-smoke
# seeds 1-3 (paired with CRD1-3)
python $S $COMMON --sample-seed 1 --out $P/artifacts/uc/47-crt-s1/CRT1 > $P/artifacts/uc/47-crt-s1.stdout.txt 2>&1
python $S $COMMON --sample-seed 2 --out $P/artifacts/uc/47-crt-s2/CRT2 > $P/artifacts/uc/47-crt-s2.stdout.txt 2>&1
python $S $COMMON --sample-seed 3 --out $P/artifacts/uc/47-crt-s3/CRT3 > $P/artifacts/uc/47-crt-s3.stdout.txt 2>&1
```
Results: push each run's `SKILLS-RESULT.json` and stdout, and the smoke's stdout, to `artifacts/ultracode-v4/results/47-crt-s<seed>/` (smoke: `47-crt-smoke/`) on branch `claude/ultracode-learning-blocker-gh011t` (`git add -f`). Pass marks: `SCREEN-v4.md`, section "arm CRT", written before the runs.
