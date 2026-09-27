@echo off
rem rsn-358s helper (sleep research thread): step 7's exact eval command, once per checkpoint (W\<R>.eval.log marks it started)
cd /d C:\Users\benja\rsn358s
if exist W\%1.eval.log exit /b 9
if exist W\%1\tests.json exit /b 9
C:\Users\benja\lis300\venv\Scripts\python.exe -B scripts/claude_rsn358s_run.py eval --ckpt W/%1/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/%1/tests.json > W\%1.eval.log 2>&1
