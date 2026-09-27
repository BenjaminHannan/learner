@echo off
rem c1-dev BensPC GPU logger (Everyday chat thread): started once by boc1dev.sh launch-chain, right after the chain.
rem One nvidia-smi line a minute to W\gpu_log.txt until W\chain.done exists (at most 5 hours); it stops itself.
cd /d C:\Users\benja\lis301\work\c1dev\tree
"C:\Program Files\Git\bin\bash.exe" handoff/kit/c1devpc/remote/boc1dev.sh gpulog
