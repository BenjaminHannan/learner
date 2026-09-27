@echo off
rem Exp 101 full one-pass run (director launches; GPU runs one job at a time).
rem Verify the GPU is free first: nvidia-smi --query-compute-apps=pid,process_name --format=csv
cd /d C:\Users\benja\talker101
py -3.10 fable_talker101_train.py --device cuda --bs 32 --ctx 512 --lr 3e-4 --warmup 500 --seed 101 --data-dir . --out full_run > full_run.log 2>&1
