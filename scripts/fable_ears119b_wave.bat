@echo off
REM Exp 119b GPU wave for BensPC (staged at C:\Users\benja\ears119b\wave119b.bat).
REM Launched DETACHED by the director (Claude) after the 119 line ends; do NOT
REM launch while another GPU job trains. Logs to wave119b.log. No installs.
REM Identical to fable_ears119_wave.bat except the data path/out dirs: the
REM data builder is fable_ears119b_data.py (remapped labels), the pool is
REM pool119b.jsonl, the work dir is ears119b, and the seeds are 11911-11913.
REM Trainer, hyper-parameters, CAL, panels, and scorer are 119 verbatim;
REM the fable_ears119b_train/score shims only rename the seed namespace
REM (11901-11903 -> 11911-11913) because 119 hardcodes its seed ids.
set W=C:\Users\benja\ears119b
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119b] pool build %date% %time% > %W%\wave119b.log 2>&1
python fable_ears119b_data.py --build-pool %W%\pool119b.jsonl --snapshot %SNAP% >> %W%\wave119b.log 2>&1 || exit /b 1
for %%s in (11911 11912 11913) do (
  echo [119b] seed %%s %date% %time% >> %W%\wave119b.log 2>&1
  python fable_ears119b_train.py --seed %%s --pool %W%\pool119b.jsonl --snapshot %SNAP% --cal %W%\repo\panels\cal.json --out %W%\runs\w-%%s >> %W%\wave119b.log 2>&1 || exit /b 1
)
python fable_ears119b_score.py --score47 --runs %W%\runs --panels47 %W%\repo\panels --snapshot %SNAP% --out %W%\report47.json --taus-out %W%\taus.json >> %W%\wave119b.log 2>&1 || exit /b 1
python fable_ears119b_score.py --score-panel --runs %W%\runs --taus %W%\taus.json --snapshot %SNAP% --panel %W%\panel.jsonl --out %W%\report119.json >> %W%\wave119b.log 2>&1 || exit /b 1
echo [119b] WAVE DONE %date% %time% >> %W%\wave119b.log 2>&1
