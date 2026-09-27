@echo off
rem y1t BensPC GPU logger (Answering-from-memory thread): started once by boy1t.sh launch-chain, right after the chain.
rem One nvidia-smi line a minute to W\gpu_log.txt until W\chain.done exists (at most 8 hours); it stops itself.
cd /d C:\Users\benja\y1t\tree
"C:\Program Files\Git\bin\bash.exe" handoff/kit/y1tpc/remote/boy1t.sh gpulog
