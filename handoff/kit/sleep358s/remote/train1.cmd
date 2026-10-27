@echo off
rem rsn-358s helper (sleep research thread): step 5's exact training command for one run, logged to W\<arm>-s<seed>.log
cd /d C:\Users\benja\rsn358s
if exist W\%1-s%2 exit /b 9
if exist W\%1-s%2.log exit /b 9
C:\Users\benja\lis300\venv\Scripts\python.exe -B scripts/claude_rsn358s_run.py train --arm %1 --seed %2 --out W/%1-s%2 > W\%1-s%2.log 2> W\%1-s%2.err
