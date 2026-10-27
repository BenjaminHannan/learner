@echo off
rem rd-378g BensPC chain (Trustworthy notes thread, 2026-09-27; handoff/kit/rd378gpc): steps 4-9b of
rem handoff/held/rd378g-pc2.md, one after another, each logged to W\<step>_log.txt with its exit code in W\steps.txt.
rem Started once (W\chain.started); W\chain.done at the end. LoCoMo files stay in %PV% (outside the tree and git).
rem dialogs, train, devcheck and write59 stop the chain on a failure; score, whenoff, g5G and g5R each stop only
rem themselves (the when-off row is report only, and G5 is scored in the cloud).
cd /d C:\Users\benja\rd378g2\tree
if exist W\chain.started exit /b 9
if not exist W mkdir W
>W\chain.started echo %date% %time%
set PYTHONUTF8=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set HF_HUB_OFFLINE=1
set PY=C:\Users\benja\lis300\venv\Scripts\python.exe
set BASE=C:/Users/benja/lis300/model
set DATA=C:/Users/benja/lis301/work/bm390/data2
set PV=C:/Users/benja/rd378g2-private
set N=artifacts/claude-rd378g-20260926
set K=handoff/kit/rd378gpc/remote/check378g.py
if not exist C:\Users\benja\rd378g2-private mkdir C:\Users\benja\rd378g2-private

>>W\steps.txt echo dialogs start %date% %time%
%PY% -B scripts/claude_rd378L_recall.py dialogs --data %DATA% --convs 5-9 --out %PV%/dialogs59.jsonl > W\dialogs_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" %PY% -B %K% dialogs-hash %PV%/dialogs59.jsonl >> W\dialogs_log.txt 2>&1
if "%RC%"=="0" set RC=%errorlevel%
>>W\steps.txt echo dialogs rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end

>>W\steps.txt echo train start %date% %time%
set G=W/g
>W\g-dir.txt echo W/g
%PY% -B scripts/claude_lis300_train.py --model %BASE% --data %N%/glm3U/rows --out W/g --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 512 --max-minutes 60 --seed 300 --merge > W\train_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" goto trained
findstr /i /c:"out of memory" W\train_log.txt >nul
if errorlevel 1 goto trained
>>W\steps.txt echo train rc=%RC% oom, retry once with --batch 8 into W/g_b8 %date% %time%
set G=W/g_b8
>W\g-dir.txt echo W/g_b8
%PY% -B scripts/claude_lis300_train.py --model %BASE% --data %N%/glm3U/rows --out W/g_b8 --epochs 2 --lr 2e-4 --rank 32 --batch 8 --max-len 512 --max-minutes 60 --seed 300 --merge >> W\train_log.txt 2>&1
set RC=%errorlevel%
:trained
>>W\steps.txt echo train rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end

>>W\steps.txt echo devcheck start %date% %time%
%PY% -B scripts/claude_rd378_write.py --model %G%/merged --dialogs %N%/glm3U/rows/dev_dialogs.jsonl --out W/gdev.jsonl > W\devcheck_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" %PY% -B %K% dev-check W/gdev.jsonl >> W\devcheck_log.txt 2>&1
if "%RC%"=="0" set RC=%errorlevel%
>>W\steps.txt echo devcheck rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end

>>W\steps.txt echo write59 start %date% %time%
%PY% -B scripts/claude_rd378_write.py --model %G%/merged --dialogs %PV%/dialogs59.jsonl --out %PV%/g59.jsonl > W\write59_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" %PY% -B %K% count %PV%/g59.jsonl >> W\write59_log.txt 2>&1
>>W\steps.txt echo write59 rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end

>>W\steps.txt echo score start %date% %time%
%PY% -B scripts/claude_rd378u_confirm.py score --data %DATA% --convs 5-9 --notes %PV%/g59.jsonl --out %PV%/outg > W\score_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo score rc=%RC% end %date% %time%

>>W\steps.txt echo whenoff start %date% %time%
%PY% -B scripts/claude_rd378g_whenoff.py score --data %DATA% --convs 5-9 --notes %PV%/g59.jsonl --out %PV%/outg_whenoff > W\whenoff_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo whenoff rc=%RC% end %date% %time%

>>W\steps.txt echo g5G start %date% %time%
%PY% -B scripts/claude_rd378_write.py --model %G%/merged --dialogs %N%/g5/dialogs.jsonl --out W/g5_G.jsonl > W\g5G_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" %PY% -B %K% count W/g5_G.jsonl >> W\g5G_log.txt 2>&1
>>W\steps.txt echo g5G rc=%RC% end %date% %time%

if not exist W\r-path.txt goto nor
set /p RP=<W\r-path.txt
>>W\steps.txt echo g5R start %date% %time%
%PY% -B scripts/claude_rd378_write.py --model %RP% --dialogs %N%/g5/dialogs.jsonl --out W/g5_R.jsonl > W\g5R_log.txt 2>&1
set RC=%errorlevel%
if "%RC%"=="0" %PY% -B %K% count W/g5_R.jsonl >> W\g5R_log.txt 2>&1
>>W\steps.txt echo g5R rc=%RC% end %date% %time%
goto end
:nor
>>W\steps.txt echo g5R skipped no-R-path %date% %time%
:end
>W\chain.done echo done %date% %time%
