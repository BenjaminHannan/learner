@echo off
rem rsn-358u helper (sleep research thread): V1 poison check, then step 7's exact eval, once per checkpoint (the logs mark each started)
cd /d C:\Users\benja\rsn358u
if exist W\%1.poison.log exit /b 9
if exist W\%1.eval.log exit /b 9
if exist W\%1\tests.json exit /b 9
C:\Users\benja\lis300\venv\Scripts\python.exe -B scripts/claude_rsn358u_run.py poison --ckpt W/%1/final.pt --out W/%1/poison.json > W\%1.poison.log 2>&1
C:\Users\benja\lis300\venv\Scripts\python.exe -B scripts/claude_rsn358u_run.py eval --ckpt W/%1/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/%1/tests.json > W\%1.eval.log 2>&1
