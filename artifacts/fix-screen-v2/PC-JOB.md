# PC job: fix screen v2 (for the Mac session to run on BensPC)

Branch: `claude/project-thread-aya9pk` (only file needed: `scripts/cap256_launch/skills_pretrain_v1.py`; copy it over the pipeline's copy in `<PIPE>/scripts/cap256_launch/`. It is a superset: defaults unchanged.)
Needs: the pipeline root used for skmain2 (`<PIPE>`, with its TRAIN-CONFIG-v2.json), the 200k seed-1 skills curriculum dir used for skmain2 (`<DATA>`), and main2's `final-checkpoint.pt` (`<M2>`). Runs one at a time (GPU-BUSY marker). No checkpoints written (`--no-checkpoint`), ~1 MB output total.

```
W=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
S=<PIPE>/scripts/cap256_launch/skills_pretrain_v1.py
COMMON="--root <PIPE> --data <DATA> --parent-path <M2> --copy-path --no-checkpoint --minutes 150"
python $S $COMMON --out artifacts/fixscreen2/Z --eval-only --updates 0 --zero-pool --dev-kinds in_dist --dev-n 5000
for s in 1 2 3; do
  python $S $COMMON --out artifacts/fixscreen2/X$s --families $W --updates 6000 --eval-every 3000 --dev-n 320 \
    --eval-at-start --fixed-rows 2000 --passes 3 --sample-seed $s --prefix-hidden 256
done
```
Smoke first (1 min): `python $S $COMMON --out artifacts/fixscreen2/smoke --families arith_bare,seq_next --sample-seed 9 --fixed-rows 20 --passes 2 --updates 40 --eval-every 20 --dev-n 10 --eval-at-start --prefix-hidden 256 --zero-pool` must print `prefix-widened` and `SKILLS-RESULT`.

Expected time: Z ~2 min; each X run ~20-30 min on the 5070 Ti; total ~1.5 h.
Results: push the four `SKILLS-RESULT.json` files (Z, X1, X2, X3) to `artifacts/fix-screen-v2/results/<run>/` on branch `claude/project-thread-aya9pk` (use `git add -f`; artifacts/ is gitignored).
