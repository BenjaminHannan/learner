# rsn-358u marks, SEALED 2026-09-27 12:27:32 UTC (sleep research thread)

The marks are exactly those in PASSMARKS-draft.md in this folder, including its section "Changes after the Thread manager's review" (V1 poison check, dead-weight disclosure, scope, G1 wording). The Thread manager reviewed the draft at 12:25 UTC and cleared it to seal after those 4 fixes. All files are sealed in SEAL-code.sha256.txt.

**PASS = V0, V1, G0, G1, G2 and G3.** V0, V1 or G0 missed = INCONCLUSIVE.
Run: BensPC, after rsn-358s. Loop and plain, seeds 13-16. Each run is trained with `python -B scripts/claude_rsn358u_run.py train --arm <arm> --seed <s> --out W/<arm>-s<s>` (defaults only), then sealed (sha256 into SEAL-run.sha256.txt), then V1 poison once, then eval once on artifacts/claude-rsn358i-20260926/tests. A run note goes in run/ at each start.
