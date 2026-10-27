# RUN-NOTE gr-9, addendum 2: re-launched after the stop was lifted

- **Why.** Ben lifted the stop at 2026-09-27T14:33:49Z ("actually wait sotp"), and the coordinator relayed it.
- **What runs.** gr-9 is re-launched once as cpu/chain-r1.sh (sha256 8fac124ed688d761ba81d0370af8eff40aa4830736eddf1312a1a3a0d4a1bc47).
- **What changed.** Nothing in the test. chain-r1.sh is the sealed chain.sh, except that it writes to run-r1/
  instead of run/. It checks the same seals and runs the same steps.
- **The stopped run.** run/ keeps only the stopped run's partial training log, and nothing is read from it.

Written 2026-09-27T14:37:04Z (date -u).
