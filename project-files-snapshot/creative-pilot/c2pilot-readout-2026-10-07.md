# C2b DEV pilot read-out (job 6, commit 95df4f6d9; DEV only; s100 / s101)

All numbers read from creative/results/c2pilot/s100.json and s101.json. Labels: shown = in the JSON; suggested = my reading; untested = not run.

## Marks as fixed in the roadmap (DEV pilot, pooled greedy first try, fits AND right)
| | s100 | s101 |
|---|---|---|
| pool T chosen (best DEV reach@32 among sameness-passing) | 3.0 | 4.0 (not 3.0) |
| dose frozen | lr 1e-3, 16 visits | lr 3e-4, 16 visits |
| leak test (corrupt every key) | pass | pass |
| PC - N (gate +15) | +40.2 [34.0, 46.9] pass | +41.8 [35.5, 48.0] pass |
| W first try (N / R / H) | 0.359 (0.012 / 0.012 / 0.000) | 0.273 (0.004 / 0.004 / 0.000) |
| W - N | +34.8 [28.9, 40.6] | +27.0 [21.5, 32.8] |
| W - R | +34.8 [28.9, 40.6] | +27.0 [21.9, 32.8] |
| reach@4 W - N | +21.1 | +5.1 |
| pooled-5 skills harm vs N (W) | 1.7 | -0.1 |
| fresh add/mult reach@32, W - N | -3.9 (0.109 -> 0.070) | -3.5 (0.113 -> 0.078) |

Pooled mark W - N >= +15 and W - R >= +10, both intervals above 0: met on both parents. Skills harm <= 2: met. Practised-kind check: W is 3.5-3.9 points below N on fresh add/mult, outside "within 2" (suggested: noise-level at 256 questions is about +-3, so this is borderline, not proven).

## Per kind, W - N greedy first try (points; each DEV kind has about 51 questions, so one question = 2 points)
| kind | s100 | s101 |
|---|---|---|
| square | +96.1 | +94.1 |
| last_digit | +78.4 | +39.2 |
| affine | +3.8 | -1.9 |
| sq_plus | +2.0 | 0.0 |
| double_add | -5.9 | +3.9 |
W-N = +34.8 points is 89 questions: square +49, last_digit +40, the three hard kinds net 0 (s100: +2, +1, -3 questions). s101: square +48, last_digit +20, hard kinds net +2 (-1, 0, +2).

LABEL. Applied literally (affine, sq_plus and double_add each within 2 points of N), neither parent gets "PASS, near-copy kinds only": affine +3.8 and double_add -5.9 on s100, double_add +3.9 on s101 are each 1-3 questions off. The code printed "PASS on pooled first try, beyond the near-copy kinds" for that reason. My reading (suggested): the rule's +-2 band is one question wide and too tight for noise; in substance the whole gain is square and last_digit, the hard kinds moved by at most 2-3 questions net, so the honest label is "PASS, near-copy kinds only". The roadmap thread owns which reading stands.

## What the gain is made of (shown)
- W is built from N's own pool hits: 365 / 210 records, of which square 257 / 149, last_digit 87 / 39, and affine 5 / 1, sq_plus 5 / 5, double_add 11 / 16. The records for the hard kinds are too few to teach much.
- R (tries that fail the check) and H (relabelled) give 0.012 / 0.004 and 0.000: no gain, so the gain needs the example check (shown). W - R equals W - N because R sits at N.
- PC (solver programs for W's questions) reaches 0.414 / 0.422; W gets 87% / 65% of that.
- N's stones taught square's first step (sq_plus stones) and mod k; those are exactly the kinds that move (suggested).

## Night 2 (report only)
W's model resamples the pool, sleeps again on 793 / 493 new hits. DEV first try right: 0.367 / 0.344 (from 0.359 / 0.273); per kind (s100 / s101): square 0.94 / 0.98, last_digit 0.82 / 0.65 (0.78 / 0.39 after night 1), affine 0.04 / 0.00, sq_plus 0.02 / 0.02, double_add 0.02 / 0.08. reach@32 double_add 0.25 / 0.08 (N 0.12 / 0.16), sq_plus 0.06 / 0.00. So no climbing onto the hard kinds (sq_plus after square, affine after double_add); the loop deepens last_digit and that is all (shown). Whether more nights or more hard-kind hits would climb: untested.

## Things the coordinator's relay did not say
- s101's pool temperature was 4.0, not 3.0; s100's was 3.0. Both are inside the widened grid, but both sit at or near the top of what was tried (6.0 was not chosen).
- After the SS sleep the practised-kind check collapsed: fresh add/mult reach@32 at T=1.0 was 0.61 / 0.57 on the warmed parent (job 5) and is 0.109 / 0.113 for N (shown). Pooled-5 skills harm is small, so the loss is in the add/mult question format of this checker, not the old skills. Cause untested.
- Dose grid is nearly flat (first try 0.39-0.42 everywhere); the 16-visit pick is a small edge, with lr differing by parent.
- Two parents on 256 DEV questions; the real C2b needs 6 paired seeds and its test stays sealed.
