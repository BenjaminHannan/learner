# PC job: T4 speed test (model-waste audit; for the Mac session, BensPC)

Marks (fixed 6:40 PM ET, `model-audit/AUDIT-ranked-2026-10-05.md` T4): PASS = >= 25% less loop time per update, first 100 updates' CE within 1e-6 of old code. WRONG = < 10% saved.
Setup as `PC-JOB-pxw.md`: copy this branch's `scripts/cap256_launch/skills_pretrain_v1.py` and `train_english_paraphrase_pilot_windows_v1.py` over the pipeline's copies; same `<PIPE>`, `<DATA>`, `<M2>`; use `GPU-BUSY.txt` and share the card (queue behind running jobs; each run ~9 GB peak, 600 updates, a few minutes).

```
P=<PIPE>; D=<DATA>; M2=<M2>
export PYTHONPATH=$P:$P/scripts:$P/scripts/cap256_launch OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
S=$P/scripts/cap256_launch/skills_pretrain_v1.py
W8=chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct
# SR2 recipe, shrunk: 200 fixed rows x 3 passes = 600 updates (same 2/3 repeat share as the real 2000 x 3)
BASE="--root $P --data $D --parent-path $M2 --no-checkpoint --copy-path --gen-fix --families $W8 --fixed-rows 200 --passes 3 --updates 600 --sample-seed 1 --eval-every 100000 --dev-n 16 --steps --steps-rich --seq-steps-v2 --profile-parts --ce-dump 100"
python $S $BASE --out $P/artifacts/uc/t4-O1  > $P/artifacts/uc/t4-O1.stdout.txt 2>&1   # old code path
python $S $BASE --out $P/artifacts/uc/t4-O2  > $P/artifacts/uc/t4-O2.stdout.txt 2>&1   # repeat of old: how deterministic is the GPU?
python $S $BASE --receipt-every 500 --out $P/artifacts/uc/t4-R > $P/artifacts/uc/t4-R.stdout.txt 2>&1      # receipts only
python $S $BASE --feat-cache 4000 --out $P/artifacts/uc/t4-C > $P/artifacts/uc/t4-C.stdout.txt 2>&1        # cache only
python $S $BASE --feat-cache 4000 --receipt-every 500 --out $P/artifacts/uc/t4-N > $P/artifacts/uc/t4-N.stdout.txt 2>&1  # both
```
Each stdout has one `skills-profile` event (seconds by part, cache hits/misses, wall_loop_seconds); each out dir has `ce-first-100.json`. Compare with:
`python scripts/cap256_launch/t4_compare.py $P/artifacts/uc` (prints saved % vs O1 and max |dCE| over 100 updates for O2, R, C, N).
Push the stdout files, the `ce-first-100.json` files and the compare output to `artifacts/ultracode-v4/results/t4/` on branch `claude/project-thread-6zalj3` (`git add -f`).
