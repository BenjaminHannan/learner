# RUN-NOTE: stage 0

- start (date -u): Tue Oct 20 01:22:06 UTC 2026
- machine: this cloud container (env beautiful-model), 4 CPUs, torch 2.14.1+cpu, CPU only, $0
- command: python scripts/premonition_reader_kv_stage0.py --out artifacts/claude-rkv-20261017/stage0
- runs: 6 (control and treated x seeds 0-2), 1500 steps each, sequential
- estimate: ~10-15 min per run, ~1-1.5 h total
- card sealed at c0bd243d3 before start
