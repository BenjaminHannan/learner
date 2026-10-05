# PC job: fix screen v3 (for the Mac session to run on BensPC)

Same setup as `../fix-screen-v2/PC-JOB.md` (same <PIPE>, <DATA>, <M2>, one run at a time, hold GPU-BUSY). Copy the branch's `scripts/cap256_launch/skills_pretrain_v1.py` (commit with "Fix screen v3" or later) over the pipeline copy again.

```
W=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
S=<PIPE>/scripts/cap256_launch/skills_pretrain_v1.py
COMMON="--root <PIPE> --data <DATA> --parent-path <M2> --copy-path --no-checkpoint --minutes 150"
# smoke (~1 min): must print lm-lora, lm-lora-first-step with A_with_grad == A_total, and SKILLS-RESULT
python $S $COMMON --out artifacts/fixscreen3/smoke --families arith_bare,seq_next --sample-seed 9 --fixed-rows 20 --passes 2 --updates 40 --eval-every 20 --dev-n 10 --eval-at-start --lm-lora 8
python $S $COMMON --out artifacts/fixscreen3/S --eval-only --updates 0 --shuffle-pool --dev-kinds in_dist --dev-n 5000
for s in 1 2 3; do
  python $S $COMMON --out artifacts/fixscreen3/A$s --families $W --updates 6000 --eval-every 3000 --dev-n 320 \
    --eval-at-start --fixed-rows 2000 --passes 3 --sample-seed $s --lm-lora 8
done
```
If the smoke shows A_with_grad below A_total (the LoRA hooks did not fire everywhere), stop and report the smoke output instead.
Expected time: S ~2 min; each A run ~20-30 min (LoRA adds a little); total ~1.5 h.
Results: push `S`, `A1`-`A3` SKILLS-RESULT.json and the smoke's stdout to `artifacts/fix-screen-v3/results/` on branch `claude/project-thread-aya9pk` (`git add -f`).
