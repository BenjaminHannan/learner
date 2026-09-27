@echo off
rem y1t BensPC chain (Answering-from-memory thread): steps 3, 4, 5 and 5b of handoff/held/benspc-y1t.md, one after another,
rem each logged to W\<step>_log.txt with its exit code in W\steps.txt. Started once (W\chain.started); W\chain.done at the end.
rem Steps 3-5 stop the chain on a failure; 5b (h1) runs whatever the DEV verdict is and stops only itself.
cd /d C:\Users\benja\y1t\tree
if exist W\chain.started exit /b 9
if not exist W mkdir W
>W\chain.started echo %date% %time%
set PYTHONUTF8=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set HF_HUB_OFFLINE=1
set PY=C:\Users\benja\lis300\venv\Scripts\python.exe
set BASE=C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
set D=artifacts/claude-y1t-20260926/glm2/items
set P=artifacts/claude-spare401-20260926/panel
>>W\steps.txt echo drafts start %date% %time%
%PY% -B scripts/claude_y1t_data.py drafts --model %BASE% --dir %D% > W\drafts_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo drafts rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end
>>W\steps.txt echo train start %date% %time%
%PY% -B scripts/claude_bm398r_train.py --base %BASE% --train %D%/train.jsonl --dev %D%/dev.jsonl --out tr > W\train_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo train rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end
>>W\steps.txt echo eval start %date% %time%
%PY% -B scripts/claude_y1g_doubt.py --model tr/merged --out eval > W\eval_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo eval rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end
>>W\steps.txt echo eval_plain start %date% %time%
%PY% -B scripts/claude_y1g_doubt.py --model %BASE% --out eval_plain > W\eval_plain_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo eval_plain rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end
>>W\steps.txt echo h1_A start %date% %time%
%PY% -B scripts/claude_y1t_h1run.py --model %BASE% --panel %P% --out h1/rows_A.jsonl > W\h1_A_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo h1_A rc=%RC% end %date% %time%
if not "%RC%"=="0" goto end
>>W\steps.txt echo h1_B start %date% %time%
%PY% -B scripts/claude_y1t_h1run.py --model tr/merged --panel %P% --out h1/rows_B.jsonl > W\h1_B_log.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo h1_B rc=%RC% end %date% %time%
:end
>W\chain.done echo done %date% %time%
