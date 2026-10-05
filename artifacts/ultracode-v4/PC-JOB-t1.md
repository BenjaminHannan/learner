# PC job: T1 (ultracode v4; the main model's lr decays; for the Mac session, BensPC)

Model-audit test T1, marks in `SCREEN-v4.md` ("audit tests T1 and T2"), written before the runs. Start when the swarm thread's runs have freed the RTX 5070 Ti (`GPU-BUSY.txt` marker shared as before). Same setup as `PC-JOB-crt.md` (copy this branch's `scripts/cap256_launch/skills_pretrain_v1.py` and `uc_diag_v4.py` over the pipeline's copies; same `<PIPE>`, `<DATA>`, `<M2>`). No new code: `--lr-final-mult` already exists.
Each run: about 20 min planner pretraining (17,000 chain rows), then 6,000 updates and the lesion evals; about 6-9 GB. Two at a time on the 16 GB card if `nvidia-smi` shows 10 GB free next to the first.

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
S=$P/scripts/cap256_launch/skills_pretrain_v1.py
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
FIT="--families $W8 --updates 6000 --eval-every 3000 --dev-n 320 --eval-at-start --fixed-rows 2000 --passes 3"
COMMON="--root $P --data $D --parent-path $M2 --no-checkpoint --minutes 170 --copy-path --gen-fix $FIT --steps --steps-rich --seq-steps-v2 --plan-route 17000 --plan-cosine --lr-final-mult 0 --final-lesions --save-texts"
for s in 4 5 6 7 8 9; do python $S $COMMON --sample-seed $s --out $P/artifacts/uc/56-t1-s$s/T1L$s > $P/artifacts/uc/56-t1-s$s.stdout.txt 2>&1; done   # or two at a time
```
Results: push each run's `SKILLS-RESULT.json` and stdout to `artifacts/ultracode-v4/results/56-t1-s<seed>/` on branch `claude/ultracode-learning-blocker-gh011t` (`git add -f`). Paired with CRDC4-9 (`results/43-crdc-s<seed>/`).
