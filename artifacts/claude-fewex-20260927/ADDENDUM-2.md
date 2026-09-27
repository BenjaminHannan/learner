# Paired replay draw correction

Written 2026-09-27 22:52 UTC, before any maze adaptation or maze panel score. Source training remains in progress.

The loop's randomized sleep round count drew from the same RNG as its replay examples. That would give loop and plain different sleep example sequences despite identical replay stores. Sleep now uses a separate RNG for round counts, leaving the example RNG paired across arms and seeds. No example, panel, pass mark, or source-training computation changes. Commit this addendum and the correction before starting adaptation; record this execution seal in RESULTS.md.
