@echo off
rem D (G1 diagnostic): free read-only measurements on G1's saved 3M and 10M B2 weights. Runs in the foreground (the chain waits for it); no training.
rem Output: WORK\results\8aG1diag (G1DIAG.md, g1diag.json, rows.jsonl, train_sample.jsonl); log appended to WORK\q8aG1diag.log. Exit code = python's.
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1
set PYTHONPATH=C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages
set CUSTOM_IO_EG2=C:\Users\benja\eg2
set CIO=C:\Users\benja\custom-io
set WORK=%CIO%\work
set POOL=%WORK%\g8a\pools\p10-rung30-s400-a64
cd /d %CIO%\src-8ag
echo %DATE% %TIME% g1diag.cmd start >> %WORK%\q8aG1diag.log
"C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe" %CIO%\g1diag\g1diag.py --src %CIO%\src-8ag --data %POOL% --train %POOL%\train.jsonl --ckpt3 %WORK%\results\8aG1d-pc\8aG1d-3M-s400\B2\checkpoint.pt --ckpt10 %WORK%\results\8aG1f-pc\8aG1f-10M-s400\B2\checkpoint.pt --result3 %WORK%\results\8aG1d-pc\8aG1d-3M-s400\B2\RESULT.json --result10 %WORK%\results\8aG1f-pc\8aG1f-10M-s400\B2\RESULT.json --out %WORK%\results\8aG1diag --device cuda --eval-batch 128 >> %WORK%\q8aG1diag.log 2>&1
set RC=%ERRORLEVEL%
echo %DATE% %TIME% g1diag.cmd end, python exit code %RC% >> %WORK%\q8aG1diag.log
exit /b %RC%
