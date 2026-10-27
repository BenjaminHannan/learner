# rsn-358k marks, SEALED 2026-09-27 14:02:21 UTC (sleep research thread)

The marks, arms, tests and design are those in PASSMARKS-draft-2.md in this folder, with PASSMARKS-draft.md for the task and the world layout. --steps is set by the rule in PILOT-RULE.md, written and committed before any pilot dev check was read. Run plan, cap and PARTIAL rule are also in PILOT-RULE.md. The Thread manager reviewed draft 2 at 14:00 UTC and cleared it to seal once the steps rule and run plan were written ("Seal after that. No need to wait for me unless you change a mark."). No mark changed.

**PASS = V, G1, G1k, G2 and G3.** V missed = INCONCLUSIVE. Proved wrong: V met and the G1k mean <= 100/300.
Train (after the pilot sets STEPS): `python -B scripts/claude_rsn358k_run.py train --arm store|nostore --seed S --steps STEPS --threads 1 --out W/<arm>-s<S>` for S in 17-20. Pasted is report only, S in 17-18. Each final.pt is sealed (sha256 into SEAL-run.sha256.txt), then evaluated once: `python -B scripts/claude_rsn358k_run.py eval --ckpt W/<R>/final.pt --tests artifacts/claude-rsn358k-20260927/tests --out W/<R>/tests.json`. Test items are never opened or printed.
All files are sealed in SEAL-code.sha256.txt.
