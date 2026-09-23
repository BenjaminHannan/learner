@echo off
REM Exp 119e score-time re-gate for BensPC (staged at C:\Users\benja\ears119e\wave119e.bat).
REM Launched DETACHED by the director (Claude); do NOT launch while another
REM GPU job trains (stop the Qwen llama-server first if it holds VRAM).
REM Scoring ONLY -- NO training. Reuses the frozen 119b checkpoints at
REM C:\Users\benja\ears119b\runs\w-1191x\ear.pt and the sealed 47 panels +
REM reading94 panel already staged for 119b. Logs to wave119e.log. No installs.
REM The ONE CHANGE vs 119b scoring: fable_ears119e_score.py --score47e applies
REM remap.json's REMAP to the 47 panels' GOLD labels at scoring time (all 10
REM panels incl. CAL), re-fits taus with the unchanged 47 rule, and re-scores
REM every 119b mark. --score-panel is the 119b reading94 scorer verbatim.
set W=C:\Users\benja\ears119e
set S=%W%\repo\scripts
set WB=C:\Users\benja\ears119b
set SNAP=C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1
cd /d %S%
echo [119e] score47e %date% %time% > %W%\wave119e.log 2>&1
python fable_ears119e_score.py --score47e --runs %WB%\runs --panels47 %WB%\repo\panels --snapshot %SNAP% --out %W%\report47e.json --taus-out %W%\taus119e.json >> %W%\wave119e.log 2>&1 || exit /b 1
python fable_ears119e_score.py --score-panel --runs %WB%\runs --taus %W%\taus119e.json --snapshot %SNAP% --panel %WB%\panel.jsonl --out %W%\report119e.json >> %W%\wave119e.log 2>&1 || exit /b 1
echo [119e] WAVE DONE %date% %time% >> %W%\wave119e.log 2>&1
