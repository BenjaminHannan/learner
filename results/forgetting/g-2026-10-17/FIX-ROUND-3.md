# Fix round 3 (coordinator GO, Oct 20: one focused round scoped to E0 and the G1 train path; $0)

Identity, flag off, 62cf9ac36 vs this commit's code (final checkpoint sha256 after 3 updates): G1 exact 3e5c13359bd13e00,
replay KL 07f65e5bc7e1bddd, A1F e0d004bb487ecc04, replay CE 8de74c6a4c3152ee: all identical, as in rounds 1-2. 58/58 tests pass.

| review 950a7d2e2 # | resolution |
|---|---|
| 6 (E0) nights_run 0 / missing -> bare KeyError | named SystemExit for both, tested |
| 7 (E0) non-atomic, stale e0.json | write_json_atomic (temp file + os.replace); written once before scoring (planned runs, replaces any older file) and after each run; tested |
| 8 (E0) wording test never read e0 | the test now requires each analyze.py template verbatim in BOTH analyze.py and e0_score.py |
| 1 (E0 tests) needed torch | tests pass night discovery in as a plain glob; the 12 E0 tests pass with `import torch` blocked |
| 2 (a) label checks late | check_priority_labels (exists + pinned sha unless --diary-any) runs before any work; tested |
| 3 (b) every >= updates silently equals the control | refused before any work; tested |
| 4, 5, 9, 10 | open, on the --replay-priority path only. The flag's help text now reads NOT FOR USE (H1 failed; findings open) |
