# PC job: PXW (ultracode v4, for the Mac session to run on BensPC)

Branch `claude/ultracode-learning-blocker-gh011t`. Copy its `scripts/cap256_launch/uc_diag_v4.py` and `scripts/cap256_launch/skills_pretrain_v1.py` over the pipeline's copies in `<PIPE>/scripts/cap256_launch/` (both are supersets; defaults unchanged).
Same `<PIPE>`, `<DATA>` (200k seed-1 skills curriculum) and `<M2>` (main2 `final-checkpoint.pt`) as `artifacts/fix-screen-v2/PC-JOB.md` on branch `claude/project-thread-aya9pk`.
Check first that `<DATA>` is the same build the Vast boxes use: `sha256sum <DATA>/train.jsonl <DATA>/dev/in_dist.jsonl` must start with `010af67124544bda` and `f975d9fb312c02d7`. If not, stop and report.
Hold `C:\Users\benja\GPU-BUSY.txt` while it runs. Expected peak GPU memory about 11 GB (17,000-row LM-feature cache), so it runs alone on the 16 GB card. No checkpoints written; output under 100 KB.

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
U=$P/scripts/cap256_launch/uc_diag_v4.py
COMMON="--mode plan --warmup 200 --fresh-core --op-attend --lr-cosine --root $P --data $D --parent-path $M2 --reader-hidden 256 --plan-fams cipher_map,fewshot_number_rule,group_induct,seq_cycle --sample-seed 1"
# smoke (~2 min): must print RESULT lines plan-reader {"hidden": 256}, plan-drop with all drops 0, plan-eval, then DIAG-DONE plan
python $U $COMMON --out $P/artifacts/uc/42-pxw-smoke --fresh-rows 200
# the run (~30-40 min)
python $U $COMMON --out $P/artifacts/uc/42-pxw-s1 --fresh-rows 17000 > $P/artifacts/uc/42-pxw-s1.stdout.txt 2>&1
# second run, PXW2048 (added 11:26 UTC): the same with the reader at 2048 instead of 256 (the later --reader-hidden wins).
# Run it after 42-pxw-s1 on the PC (each needs about 11 GB, so not both at once on 16 GB), or at the same time on the M1 Pro if the pipeline runs there (about 3x slower).
python $U $COMMON --reader-hidden 2048 --out $P/artifacts/uc/44-pxw2048-s1 --fresh-rows 17000 > $P/artifacts/uc/44-pxw2048-s1.stdout.txt 2>&1
```
Results: push each run's `DIAG-plan.json` and stdout (`42-pxw-s1`, `44-pxw2048-s1`) to `artifacts/ultracode-v4/results/<run>/` on branch `claude/ultracode-learning-blocker-gh011t` (`git add -f`; artifacts/ is gitignored). Pass marks: `artifacts/ultracode-v4/DIAG-v4.md`, sections "PXW" and "PXW2048", written before the runs.

## Added 12:25 UTC: 48-pxh-s1 (two-hop content-addressed pointer; marks: DIAG-v4.md section "PXH")
Needs commit with `--ptr-hops` (after 01b222e4a). Reader 32 (no `--reader-hidden`), else the same as PXW; about 11 GB, so not alongside another 11 GB job on the 16 GB card (or run it on the M1 Pro).
```
COMMON_H="--mode plan --warmup 200 --fresh-core --op-attend --lr-cosine --root $P --data $D --parent-path $M2 --plan-fams cipher_map,fewshot_number_rule,group_induct,seq_cycle --sample-seed 1 --ptr-hops 2"
# smoke (~2 min): must print RESULT plan-ptr-hops {"hops": 2, "added_params": 116678}, plan-eval, then DIAG-DONE plan
python $U $COMMON_H --out $P/artifacts/uc/48-pxh-smoke --fresh-rows 200
python $U $COMMON_H --out $P/artifacts/uc/48-pxh-s1 --fresh-rows 17000 > $P/artifacts/uc/48-pxh-s1.stdout.txt 2>&1
```
Push `DIAG-plan.json` and stdout to `artifacts/ultracode-v4/results/48-pxh-s1/`.
