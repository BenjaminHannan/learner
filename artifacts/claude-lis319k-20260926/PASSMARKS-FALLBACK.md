# lis-319k fallback, fixed 2026-09-26 ~14:30 UTC, before the lis-319k read exists
If lis-319k FAILS only on K2, K3 or K4 (too many wrong or stale saves), score lis-319k2 from the same single read:
CORRECT-mode facts save at 0.98 instead of 0.95 (`claude_lis319k_score.py bar --at 0.98`), same marks K1-K4, same
judges (its saves are a subset of lis-319k's). If lis-319k FAILS on K1 (fewer than +5 corrections), no bar change is
tried: the next step is the dev-bank diagnosis (artifacts/claude-lis319k-20260926/devbank) to see whether missed
corrections are misread rather than below the bar.
