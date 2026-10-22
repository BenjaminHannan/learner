# PC job: B1 TEACH data (teacher = LFM2.5-1.2B-Instruct, plain transformers, no vllm)

Goal: write and answer ~120k+ teacher items on the 5070 Ti, filter to 200,000 question rows. Resumable: re-running the same command continues.
The card is shared: bf16 1.2B + batch 192 uses about 5-6 GB; it fits beside other jobs. Hold C:\Users\benja\GPU-BUSY.txt only if the other jobs on it say so (this job is small).

1. Get the code: `git clone --branch claude/b1-teach-gen-data https://github.com/BenjaminHannan/learner.git C:\Users\benja\b1_teach_repo` (or fetch that branch in an existing clone).
2. Use the same Python as the other jobs (base 3.10 + lis300 venv on PYTHONPATH: torch 2.11 cu128, transformers 5.17). Nothing to install.
3. Run, from `C:\Users\benja\b1_teach_repo\b1_teach`, logging to a file, in the background (it takes hours):
   `python teach.py --out C:\Users\benja\b1_teach_out --backend hf --batch 192 > C:\Users\benja\b1_teach_out.log 2>&1`
   If CUDA out of memory: rerun with `--batch 96`.
4. Progress is in the log ("wrote N/M", "answered N/M") and the files `C:\Users\benja\b1_teach_out\writes_r*.jsonl`, `answers_r*.jsonl`.
5. When it prints "kept ...", it has written `teach_200k.jsonl` and `teach_report.json` there. Then copy `C:\Users\benja\b1_teach_out` to the Mac or push as a tarball to /mnt/project-files/plan-b/data/raw/ (about 300 MB).
6. Do not delete anything else on the PC. Nothing here touches GOLD/reserved/blind panels.
