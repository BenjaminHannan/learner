# All-words + pointer exit with generated practice, on BensPC: pass marks (fixed before any run)

Ask: coordinator relay 2026-10-04 (pick defaults, fast lane): port the cloud recipe (branch claude/project-thread-ajo58u, reasoner_ptr/real/english/, rounds 4-5: allptr arm + 8000 generated practice rows per seed, 2000 updates x 16 rows, lr 1e-3, FRESH-EN-R3.json 192 questions) to the PC GPU; start from the main2 skills checkpoint if it plugs in, else from scratch.
Code: cloud run_english.py unchanged except one added flag --init-ckpt (strict-ish load of core/reader/prefix/tool from a pilot-shaped checkpoint; hard error if any key is missing or unexpected). Modules are the same real pipeline files (sha-identical to the PC package).

Arms (6 paired seeds 0-5 each, same generator seeds 1000+seed):
- S = from scratch (the cloud round-4 recipe replicated on the PC).
- M = initialised from artifacts/skills/main2/final-checkpoint.pt (only if it loads with no missing/unexpected keys; otherwise M is reported as "does not plug in" and not run).
Reference: bare 1.2B LM shown the same 8 bank examples (lm_fewshot), run once on the PC (deterministic). Cloud number for it: 75.0%.

Judged (fresh exact accuracy over the 192 fresh questions, mean over 6 seeds):
- PASS for an arm: mean >= lm_fewshot + 5 points. FAIL: mean below lm_fewshot. Between: inconclusive.
- "Skills initialisation helps" (M vs S, paired by seed): only if mean(M-S) >= +3 points AND the 95% t-interval (df 5, t = 2.571) lower bound > 0. "No help": interval includes 0. "Hurts": upper bound < 0.
Read, not judged: contains accuracy, new-word answers, per-family, train fit, the generated held-out panel, zero-pool lesion, NEW-KINDS-R5 (extra-eval) accuracy.
Limits: in-family test (the fresh set and generator share six question kinds); the talker sees every prompt word (allptr), so the frozen LM does part of the reading; fresh set written by helper agents, not sealed; fast lane. This is the English-comprehension toy, separate from the village model. Never touches GOLD/reserved/blind panels.
