# PC setup: the two files T1 (and the speed thread's T4) need on BensPC

Both come from git, the same way the Vast boxes get them (`scripts/cap256_launch/ultracode_box.sh`). Nothing needs renting.

## 1. Skills data: check the existing copy first (probably fine)
`C:\Users\benja\skills-data` likely IS the right build. The builder (`skills_curriculum/build.py` `_dump`, branch `claude/project-thread-y0sxwe`) hashes each line in memory with "\n" endings, but on Windows `open(path, "w")` writes "\r\n", so `sha256sum` of the file differs even when the content is identical. Check with line endings normalised:

```
python -c "import hashlib; d=r'C:\Users\benja\skills-data'; [print(f, hashlib.sha256(open(d+'/'+f,'rb').read().replace(b'\r\n', b'\n')).hexdigest()[:16]) for f in ('train.jsonl','dev/in_dist.jsonl')]"
```
Must print `010af67124544bda` and `f975d9fb312c02d7`. Also `manifest.json` in that folder should list `train.jsonl: 010af671...` under `files_sha256`.
- If both match: use it as `<DATA>`, and run the jobs with `PYTHONUTF8=1` set (so Python reads the files as UTF-8, which is what the normalised hash proves they are).
- If not: rebuild into a new folder (keep the old one; never delete data):
```
git clone -c core.autocrlf=false --depth 1 --filter=blob:none --sparse -b claude/project-thread-y0sxwe https://github.com/BenjaminHannan/learner C:\Users\benja\uc-cur
cd C:\Users\benja\uc-cur && git sparse-checkout set skills_curriculum
set PYTHONUTF8=1
python -m skills_curriculum.build --out C:\Users\benja\skills-data-v1 --train 200000 --dev-per-cell 40 --seed 1
```
then the normalised check above on `skills-data-v1` must give the same two prefixes.

## 2. main2 checkpoint (60.7 MB, plain git file)
```
git clone -c core.autocrlf=false --depth 1 --filter=blob:none --sparse -b claude/real-pipeline-checkpoints https://github.com/BenjaminHannan/learner C:\Users\benja\uc-ckpt
cd C:\Users\benja\uc-ckpt && git sparse-checkout set skills/main2
git hash-object skills/main2/final-checkpoint.pt
```
The last line must print `ef708d0d2209f0202da28ea3090ab752bbdea2e7`. Then `<M2>` = `C:\Users\benja\uc-ckpt\skills\main2\final-checkpoint.pt`.

## 3. Pipeline (`<PIPE>`)
Use the pipeline root the PC used for skmain2 if it still exists, and copy this branch's `scripts/cap256_launch/skills_pretrain_v1.py` and `uc_diag_v4.py` over its copies. If it is gone: `git sparse-checkout set pipeline skills/main2` in `uc-ckpt` instead (core.autocrlf=false matters: the code checks pinned file hashes), and point `pipeline/configs/english-pilot-v1/TRAIN-CONFIG-v2.json` `lm.model_path` at the cached LiquidAI/LFM2.5-1.2B-Instruct snapshot (revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b), copied to `pipeline/artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1/TRAIN-CONFIG-v2.json` as the box does.

Then run `PC-JOB-t1.md` (smoke first is optional: the same flags with `--fixed-rows 20 --passes 2 --updates 40 --eval-every 40 --dev-n 16 --plan-route 300` must end with SKILLS-RESULT).
