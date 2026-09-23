@echo off
REM Exp 119f GPU wave for BensPC (staged at C:\Users\benja\ears119f\wave119f.bat).
REM Launched DETACHED by the director (Claude) after the reading94b panel is
REM sealed; do NOT launch while another GPU job trains (stop the Qwen
REM llama-server first if it holds VRAM). Logs to wave119f.log. No installs.
REM THE ONE CHANGE vs 119b (training data only): the pool is built by
REM fable_ears119f_data.py (5,000 panel-shaped occupation rows replace 5,000
REM synth STATE rows 1:1; pool size, steps, recipe unchanged). Scoring is the
REM 119e logic: 47 panels with remapped golds, taus by the 47 rule on CAL
REM only, then W2/W3 on BOTH panels (reading94 + registered reading94b).
set W=C:\Users\benja\ears119f
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119f] pool build %date% %time% > %W%\wave119f.log 2>&1
python fable_ears119f_data.py --build-pool %W%\pool119f.jsonl --snapshot %SNAP% >> %W%\wave119f.log 2>&1 || exit /b 1
for %%s in (11911 11912 11913) do (
  echo [119f] seed %%s %date% %time% >> %W%\wave119f.log 2>&1
  python fable_ears119f_train.py --seed %%s --pool %W%\pool119f.jsonl --snapshot %SNAP% --cal %W%\repo\panels\cal.json --out %W%\runs\w-%%s >> %W%\wave119f.log 2>&1 || exit /b 1
)
echo [119f] score47e %date% %time% >> %W%\wave119f.log 2>&1
python fable_ears119f_score.py --score47e --runs %W%\runs --panels47 %W%\repo\panels --snapshot %SNAP% --out %W%\report47f.json --taus-out %W%\taus119f.json >> %W%\wave119f.log 2>&1 || exit /b 1
echo [119f] panel94 %date% %time% >> %W%\wave119f.log 2>&1
python fable_ears119f_score.py --score-panel --runs %W%\runs --taus %W%\taus119f.json --snapshot %SNAP% --panel %W%\panel94.jsonl --panel-tag 94 --w3-base-bars 27,33,30 --w3-need 2 --w2-min-correct 30 --w2-need 2 --out %W%\report119f_94.json >> %W%\wave119f.log 2>&1 || exit /b 1
echo [119f] panel94b %date% %time% >> %W%\wave119f.log 2>&1
python fable_ears119f_score.py --score-panel --runs %W%\runs --taus %W%\taus119f.json --snapshot %SNAP% --panel %W%\panel94b.jsonl --panel-tag 94b --w3-base-bars 27,33,30 --w3-need 3 --w2-min-correct 0 --w2-need 2 --out %W%\report119f_94b.json >> %W%\wave119f.log 2>&1 || exit /b 1
echo [119f] WAVE DONE %date% %time% >> %W%\wave119f.log 2>&1
