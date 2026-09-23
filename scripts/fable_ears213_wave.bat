@echo off
REM Exp 213 GPU wave for BensPC (staged at C:\Users\benja\ears213\wave213.bat).
REM Launched DETACHED by the director after the seal; do NOT launch while
REM another GPU job trains (stop the Qwen llama-server first if it holds
REM VRAM). Logs to wave213.log. No installs, no training (frozen
REM checkpoints, scorer side only).
REM PART A (fix): table-only render (scripts/fable_ears213_relmap.py) — the
REM verdict/decode path is verbatim by import, so registered verdicts cannot
REM change (A2 re-verifies). PART B (measurement): per-seed LTT gate on cal
REM ONLY for alpha in {0.01,0.02,0.05}, sealed to taus213_*.json BEFORE any
REM test panel is opened (enforced in-process), then t_seen / t_new /
REM reading94 / reading94b at the sealed taus and the old tau side by side.
REM Reading panels: aggregate counts only, never sentences.
set W=C:\Users\benja\ears213
set S=%W%\repo\scripts
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
set G119=C:\Users\benja\ears119g
cd /d %S%
echo [213] probe %date% %time% > %W%\wave213.log 2>&1
python fable_ears213_score.py --probe %W%\probe213_cases.json --out %W%\probe213_out.json >> %W%\wave213.log 2>&1 || exit /b 1
echo [213] wave-119g %date% %time% >> %W%\wave213.log 2>&1
python fable_ears213_score.py --wave --model 119g --runs %G119%\runs --snapshot %SNAP% --panels47 %W%\repo\panels --panel94 %W%\panel94.jsonl --panel94b %W%\panel94b.jsonl --taus-old %G119%\taus119g.json --expect47 %G119%\report47g.json --taus-out %W%\taus213_119g.json --out %W%\report213_119g.json >> %W%\wave213.log 2>&1 || exit /b 1
echo [213] wave-119h %date% %time% >> %W%\wave213.log 2>&1
python fable_ears213_score.py --wave --model 119h --runs %W%\runs --snapshot %SNAP% --panels47 %W%\repo\panels --panel94 %W%\panel94.jsonl --panel94b %W%\panel94b.jsonl --taus-old %W%\taus119h.json --expect47 %W%\report47h.json --taus-out %W%\taus213_119h.json --out %W%\report213_119h.json >> %W%\wave213.log 2>&1 || exit /b 1
echo [213] WAVE DONE %date% %time% >> %W%\wave213.log 2>&1
