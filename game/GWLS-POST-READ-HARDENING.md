# GW-LS read path: post-read hardening list (Q115). Proven INERT for the one sealed read; does not hold it.
From the Q115 re-review (28f6fcc42..8680fb335) and the P1-P6 verifier. Each is inert under `game/GWLS-READ-PRECONDITIONS.md`.

1. Score files and the completed record are persisted before the identity check (gwls_final.py:851). Inert: inputs are pinned by sha256
   and there is a single operator, so identity passes.
2. Bare asserts vanish under `-O` (gwls_report.py:174, compare, `codes == [0, 0]`, verdict). Inert: no `-O`, `PYTHONOPTIMIZE` unset.
   Hardening: `if sys.flags.optimize: sys.exit(...)` at the top of main.
3. The gate does not refuse when the two readings of the sealed round-4 sentence disagree (gwls_report.py:241). Inert: both readings
   say CONTINUE (ratio 3.04 / 7.02, non-habit 5.75 / 6.15).
4. The pgrep fallback is not filtered by seed folder (gwls_final.py:290). Inert: /proc is in use; and the fallback fails closed.
5. `gwls_persist.sh` falls back to a python3 without torch and still exits 0 (:20). Inert: not part of the read.
6. The gate computes the full census twice (gwls_report.py:178); efficiency only.
7. `ratio_w_exact` duplicates `census_rows`; altitude only.
8. Duplicate `sha256_file` (gwls_final.py:524); reuse only.
9. Dead `load_games`, and the `cap_problems` alias; cleanup only.
10. From the P1-P6 verifier:
    - the scorer re-reads constants.json after the checks;
    - the previous-read and overwrite checks have no cross-process lock;
    - root final.json is written non-atomically;
    - `persist()` copies score files only to `--persist-dir`;
    - the hidepid check is blunt;
    - round8 checks use `os.path.exists` (fails closed).

    All inert: single operator, nothing edited mid-run.
11. Earlier deferrals:
    - review finding 5 (gwls.sh 5-s start check);
    - `gwls_checks` exits 0 on FAIL;
    - `gwls_persist.sh` relative root;
    - `gwls_checks` double read.
