# PC job: WD (ultracode v4; both doors at 2048; for the Mac session, BensPC)

Same setup as `PC-JOB-pxw.md` (same branch files copied over the pipeline, same `<PIPE>`, `<DATA>`, `<M2>`, data hash check, GPU-BUSY marker shared with the custom reader/talker thread). Each run uses about 6-9 GB, so **two run at once** on the 16 GB card when nothing else is on it; check free memory first. Each run takes about 50-60 min.

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
S=$P/scripts/cap256_launch/skills_pretrain_v1.py
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
FIT="--families $W8 --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
COMMON="--root $P --data $D --parent-path $M2 --no-checkpoint --minutes 170 --copy-path --gen-fix $FIT --steps --steps-rich --seq-steps-v2 --reader-hidden 2048 --prefix-hidden 2048 --final-lesions --save-texts"
# smoke (~2 min): must print the widened reader/prefix lines and SKILLS-RESULT
python $S --root $P --data $D --parent-path $M2 --no-checkpoint --copy-path --gen-fix --families $W8 --fixed-rows 20 --passes 2 --updates 40 --eval-every 40 --dev-n 16 --sample-seed 9 --steps --reader-hidden 2048 --prefix-hidden 2048 --out $P/artifacts/uc/45-wd-smoke
# seeds 1 and 2 together, then seed 3
python $S $COMMON --sample-seed 1 --out $P/artifacts/uc/45-wd-s1/WD1 > $P/artifacts/uc/45-wd-s1.stdout.txt 2>&1 &
python $S $COMMON --sample-seed 2 --out $P/artifacts/uc/45-wd-s2/WD2 > $P/artifacts/uc/45-wd-s2.stdout.txt 2>&1 &
wait
python $S $COMMON --sample-seed 3 --out $P/artifacts/uc/45-wd-s3/WD3 > $P/artifacts/uc/45-wd-s3.stdout.txt 2>&1
```
Results: push each run's `SKILLS-RESULT.json` and stdout to `artifacts/ultracode-v4/results/45-wd-s<seed>/` on branch `claude/ultracode-learning-blocker-gh011t` (`git add -f`). Pass marks: `SCREEN-v4.md`, section "arm WD", written before the runs.
Order on the PC: after `42-pxw-s1`. If `44-pxw2048-s1` cannot run on the M1, run it after these.
