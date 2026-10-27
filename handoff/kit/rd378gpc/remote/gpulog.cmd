@echo off
rem rd-378g BensPC GPU logger (Trustworthy notes thread; from the y1t kit): started once by bo378g.sh launch-chain, right
rem after the chain. One nvidia-smi line a minute to W\gpu_log.txt until W\chain.done exists (at most 6 hours).
cd /d C:\Users\benja\rd378g2\tree
"C:\Program Files\Git\bin\bash.exe" handoff/kit/rd378gpc/remote/bo378g.sh gpulog
