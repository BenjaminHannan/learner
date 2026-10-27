# feas-24b: feas-24 with a converged head fit (registered 2026-09-25 ~20:15 UTC, before the run)

Why: feas-24 (VERIFY-feas24.md, NOT SHOWN) did not test its idea. Its reused gradient-descent fitter diverged
(training loss 8-47 against 0.69 at the start), so its pair counts were chaotic and changed with the CPU thread count.
ONE change: the head is fitted by damped Newton's method on the same L2-penalised logistic loss, and each fit reports
its final gradient size. Selection uses dev only: layer (8/12/16/20/24) and l2 (10/100/1,000/10,000) with the best
mean dev AUC over the three seeds' real-label heads. Everything else is feas-24: states, text, features, split rule,
matched pairs, the shuffled-label placebo, seeds 0/1/2, and the marks. The panel is fresh (split seed 792), because
the seed-791 test pairs were scored once already. Script: scripts/claude_feas24b.py.
Checked before registering: the selftest converges (gradient 6e-13 on a 1,536-wide case). On feas-24's OLD dev
split only (never its test pairs), the Newton fit took 1-2 s, converged (gradient ~1e-13) and had dev AUC 0.79-0.81
at layer 12.

Marks (unchanged from feas-24; 200 matched pairs, 100 with 3 values and 100 with 2; ties count half):
- PASS = in EVERY seed: real-label head right on at least 150/200, AND at least 30 more than the same seed's
  shuffled-label head, AND at least 70/100 on the 3-value pairs.
- Proved wrong: real-label head at 110/200 or fewer in all three seeds AND no more than 10 above shuffled.
- Otherwise: NOT SHOWN.
- Invalid (reported as NO RESULT): any test fit with a final gradient above 1e-4 (not converged).
- Reproducibility check after the run: re-score from the cached features with a different CPU thread count; the
  pair counts must match exactly, else NO RESULT.
One CPU run in the creative thread's container.
