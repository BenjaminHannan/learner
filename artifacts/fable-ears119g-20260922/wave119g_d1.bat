@echo off
REM Exp 119g GPU wave for BensPC (staged at C:\Users\benja\ears119g\wave119g.bat).
REM Launched DETACHED by the director after the seal; do NOT launch while
REM another GPU job trains (stop the Qwen llama-server first if it holds
REM VRAM). Logs to wave119g.log. No installs.
REM THE ONE CHANGE vs 119f (model only): RelCondEars (relation-conditioned
REM span pointers, U=0 at init) + teacher-forced gold relation in training +
REM multi-fact decode at score time (K=3, FLOOR=0.10 sealed; K=1 always
REM reported). Same pool (built by fable_ears119f_data.py), same seeds,
REM steps, lr, batch, epochs, same 47 gate/taus rule, same scorer logic.
set W=C:\Users\benja\ears119g
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119g] step0-119f-baseline %date% %time% > %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --step0 --runs119f C:\Users\benja\ears119f\runs --taus119f C:\Users\benja\ears119f\taus119f.json --snapshot %SNAP% --panel94b %W%\panel94b.jsonl --out %W%\step0_119f.json >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] pool build %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119f_data.py --build-pool %W%\pool119f.jsonl --snapshot %SNAP% >> %W%\wave119g.log 2>&1 || exit /b 1
for %%s in (11911 11912 11913) do (
  echo [119g] seed %%s %date% %time% >> %W%\wave119g.log 2>&1
  python fable_ears119g_train.py --seed %%s --pool %W%\pool119f.jsonl --snapshot %SNAP% --cal %W%\repo\panels\cal.json --out %W%\runs\w-%%s >> %W%\wave119g.log 2>&1 || exit /b 1
)
echo [119g] score47g %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --score47g --runs %W%\runs --panels47 %W%\repo\panels --snapshot %SNAP% --out %W%\report47g.json --taus-out %W%\taus119g.json --k 3 --floor 0.10 >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] panel94-K1 %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --score-panel --runs %W%\runs --taus %W%\taus119g.json --snapshot %SNAP% --panel %W%\panel94.jsonl --panel-tag 94 --k 1 --floor 0.0 --out %W%\report119g_94_K1.json >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] panel94-K3 %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --score-panel --runs %W%\runs --taus %W%\taus119g.json --snapshot %SNAP% --panel %W%\panel94.jsonl --panel-tag 94 --k 3 --floor 0.10 --out %W%\report119g_94_K3.json >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] panel94b-K1 %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --score-panel --runs %W%\runs --taus %W%\taus119g.json --snapshot %SNAP% --panel %W%\panel94b.jsonl --panel-tag 94b --k 1 --floor 0.0 --out %W%\report119g_94b_K1.json >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] panel94b-K3 %date% %time% >> %W%\wave119g.log 2>&1
python fable_ears119g_score_d1.py --score-panel --runs %W%\runs --taus %W%\taus119g.json --snapshot %SNAP% --panel %W%\panel94b.jsonl --panel-tag 94b --k 3 --floor 0.10 --out %W%\report119g_94b_K3.json >> %W%\wave119g.log 2>&1 || exit /b 1
echo [119g] WAVE DONE %date% %time% >> %W%\wave119g.log 2>&1
