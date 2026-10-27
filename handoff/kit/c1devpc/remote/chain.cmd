@echo off
rem c1-dev BensPC chain (Everyday chat thread): the four arms of artifacts/claude-c1dev-20260927/PLAN.md, D T Q L, one
rem after another, each through the winnl2 and twin-b wrappers into outC1\chat_<arm>.jsonl, logged to W\log<arm>.txt with
rem its exit code in W\steps.txt. An arm that exits non-zero is run once more (the runner skips conversations already
rem written) into W\log<arm>-retry.txt; the chain then goes on to the next arm. Started once (W\chain.started);
rem W\chain.done at the end. Eval only: no training, no weights written.
cd /d C:\Users\benja\lis301\work\c1dev\tree
if exist W\chain.started exit /b 9
if not exist W mkdir W
if not exist outC1 mkdir outC1
>W\chain.started echo %date% %time%
set PYTHONUTF8=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set HF_HUB_OFFLINE=1
set PY=C:\Users\benja\lis300\venv\Scripts\python.exe
set BASE=C:/Users/benja/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
set Q2DIR=C:/Users/benja/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
set L12DIR=C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
set RUN=%PY% -B scripts/claude_winnl2_wrap.py scripts/claude_twinb_wrap.py scripts/claude_ch403_run.py run --panel-dir artifacts/claude-chatdev-20260926 --out outC1
call :arm D claude_c1dev_talker:build_talker02d %BASE%
call :arm T twin %BASE%
call :arm Q twin %Q2DIR%
call :arm L twin %L12DIR%
>W\chain.done echo done %date% %time%
exit /b 0

:arm
>>W\steps.txt echo %1 start %date% %time%
%RUN% --arm %2 --name %1 --gen-model %3 > W\log%1.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo %1 rc=%RC% end %date% %time%
if "%RC%"=="0" exit /b 0
>>W\steps.txt echo %1-retry start %date% %time%
%RUN% --arm %2 --name %1 --gen-model %3 > W\log%1-retry.txt 2>&1
set RC=%errorlevel%
>>W\steps.txt echo %1-retry rc=%RC% end %date% %time%
exit /b 0
