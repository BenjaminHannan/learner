# RUN-NOTE: stage 0 (after Addendum A)

- start (date -u): Tue Oct 20 01:46:26 UTC 2026
- machine: this cloud container (env beautiful-model), 4 CPUs, torch 2.14.1+cpu, CPU only, $0
- command: python scripts/premonition_reader_kv_stage0.py --out artifacts/claude-rkv-20261017/stage0
- runs: 6 (control then step-matched treated, seeds 0-2), 1500-step budget, sequential
- estimate: ~9-10 min per run, ~1 h total
- card re-sealed (SEAL-v2) at 7de83cf5f before start
- finished (date -u): Tue Oct 20 02:43:16 UTC 2026
- exit 0; 6 runs, all counted (made at 7de83cf5f, runner review CLEAN)
