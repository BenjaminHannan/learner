@echo off
REM Exp 119h GPU wave for BensPC (staged at C:\Users\benja\ears119h\wave119h.bat).
REM Launched DETACHED by the director after the seal; do NOT launch while
REM another GPU job trains (stop the Qwen llama-server first if it holds
REM VRAM). Logs to wave119h.log. No installs.
REM THE ONE CHANGE vs 119g (data only): varied-shape occupation rows
REM (scripts/fable_ears119h_data.py: is/was, birth brackets, modifiers,
REM demonyms, job lists, multi-word jobs; one row per stated fact) replace
REM the same 5,000 STATE slots 1:1. Same RelCondEars model (by import),
REM same teacher-forced relation, same recipe/seeds/steps/lr/batch/epochs,
REM same K=3/FLOOR=0.10 (sealed in 119g, not re-chosen), same 47 gate rule.
REM No step 0: the 119g registered numbers are the baseline.
set W=C:\Users\benja\ears119h
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119h] pool build %date% %time% > %W%\wave119h.log 2>&1
python fable_ears119h_data.py --build-pool %W%\pool119h.jsonl --snapshot %SNAP% >> %W%\wave119h.log 2>&1 || exit /b 1
for %%s in (11911 11912 11913) do (
  echo [119h] seed %%s %date% %time% >> %W%\wave119h.log 2>&1
  python fable_ears119h_train.py --seed %%s --pool %W%\pool119h.jsonl --snapshot %SNAP% --cal %W%\repo\panels\cal.json --out %W%\runs\w-%%s >> %W%\wave119h.log 2>&1 || exit /b 1
)
echo [119h] score47h %date% %time% >> %W%\wave119h.log 2>&1
python fable_ears119h_score.py --score47g --runs %W%\runs --panels47 %W%\repo\panels --snapshot %SNAP% --out %W%\report47h.json --taus-out %W%\taus119h.json --k 3 --floor 0.10 >> %W%\wave119h.log 2>&1 || exit /b 1
echo [119h] panel94b-K1 %date% %time% >> %W%\wave119h.log 2>&1
python fable_ears119h_score.py --score-panel --runs %W%\runs --taus %W%\taus119h.json --snapshot %SNAP% --panel %W%\panel94b.jsonl --panel-tag 94b --k 1 --floor 0.0 --out %W%\report119h_94b_K1.json >> %W%\wave119h.log 2>&1 || exit /b 1
echo [119h] panel94b-K3 %date% %time% >> %W%\wave119h.log 2>&1
python fable_ears119h_score.py --score-panel --runs %W%\runs --taus %W%\taus119h.json --snapshot %SNAP% --panel %W%\panel94b.jsonl --panel-tag 94b --k 3 --floor 0.10 --out %W%\report119h_94b_K3.json >> %W%\wave119h.log 2>&1 || exit /b 1
echo [119h] panel94-K1 %date% %time% >> %W%\wave119h.log 2>&1
python fable_ears119h_score.py --score-panel --runs %W%\runs --taus %W%\taus119h.json --snapshot %SNAP% --panel %W%\panel94.jsonl --panel-tag 94 --k 1 --floor 0.0 --out %W%\report119h_94_K1.json >> %W%\wave119h.log 2>&1 || exit /b 1
echo [119h] panel94-K3 %date% %time% >> %W%\wave119h.log 2>&1
python fable_ears119h_score.py --score-panel --runs %W%\runs --taus %W%\taus119h.json --snapshot %SNAP% --panel %W%\panel94.jsonl --panel-tag 94 --k 3 --floor 0.10 --out %W%\report119h_94_K3.json >> %W%\wave119h.log 2>&1 || exit /b 1
echo [119h] WAVE DONE %date% %time% >> %W%\wave119h.log 2>&1
