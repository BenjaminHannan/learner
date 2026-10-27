# Do not run scripts/claude_rsn358b_sudoku.py as it stands on torch 2.8 (2026-09-26 17:21 UTC, sleep research thread)

Its loop training runs no-grad free rounds (sup_step, :145-150) inside the same bf16 autocast block as the graded round (:172, :192). On torch 2.8, the rent-kit image, autocast's weight cache then leaves the loop's layer weights with no gradient (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md).

It has never run: no results exist. Before it ever runs, it needs the same repair as rsn-358i2 and 358t v3: autocast with cache_enabled=False, or a wrapper that imports scripts/claude_rsn358i2_run.py's NoCacheAutocast first. It also needs torch.__version__ logged in its summary. That is a new sealed file, never an edit to this one.
