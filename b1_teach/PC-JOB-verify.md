# Job: B1 TEACH yes/no verification (1.2B teacher, plain transformers, ~100k short prompts, no big VRAM)

Run after the B2 confirm queue on the PC, or on the Mac once its current job ends, whichever machine frees first. Same checkout as PC-JOB-teach.md (branch claude/b1-teach-gen-data, folder b1_teach, pull latest).
Input: the TEACH file teach_200k.jsonl (171,940 rows, results/teach_200k.jsonl.gz in the branch; gunzip it).

1. `python verify.py --inp <path>\teach_200k.jsonl --out <outdir> --batch 192 > <outdir>.log 2>&1`   (Mac/MPS: --batch 32)
   Resumable; it checks every yes/no row twice (passage, paraphrase). Progress lines "N/M".
2. When done: `python verify.py --inp <path>\teach_200k.jsonl --out <outdir> --finalize` (CPU, seconds). It prints counts and writes teach_verified_all.jsonl.
3. Push <outdir>/verify_yn.jsonl (gzipped is fine) and teach_verified_all.jsonl.gz to branch claude/b1-teach-gen-data under b1_teach/results/ (or send path). I export from there.
