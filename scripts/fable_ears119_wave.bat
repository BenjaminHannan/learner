@echo off
REM Exp 119 GPU wave for BensPC (staged at C:\Users\benja\ears119\wave119.bat).
REM Launched DETACHED by Claude after the talker run ends (~04:00); do NOT
REM launch while another GPU job trains. Logs to wave119.log. No installs.
set W=C:\Users\benja\ears119
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119] pool build %date% %time% > %W%\wave119.log 2>&1
python fable_ears119_data.py --build-pool %W%\pool119.jsonl --snapshot %SNAP% >> %W%\wave119.log 2>&1 || exit /b 1
for %%s in (11901 11902 11903) do (
  echo [119] seed %%s %date% %time% >> %W%\wave119.log 2>&1
  python fable_ears119_train.py --seed %%s --pool %W%\pool119.jsonl --snapshot %SNAP% --cal %W%\repo\panels\cal.json --out %W%\runs\w-%%s >> %W%\wave119.log 2>&1 || exit /b 1
)
python fable_ears119_score.py --score47 --runs %W%\runs --panels47 %W%\repo\panels --snapshot %SNAP% --out %W%\report47.json --taus-out %W%\taus.json >> %W%\wave119.log 2>&1 || exit /b 1
python fable_ears119_score.py --score-panel --runs %W%\runs --taus %W%\taus.json --snapshot %SNAP% --panel %W%\panel.jsonl --out %W%\report119.json >> %W%\wave119.log 2>&1 || exit /b 1
echo [119] WAVE DONE %date% %time% >> %W%\wave119.log 2>&1
