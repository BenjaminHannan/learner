# bridgelab summary

Accuracy %, mean+-sd over seeds. Chance = 12.5%. Direction A->B = head B (needs v from A); B->A = head A (needs u from B).
Probe: A->B message -> v; B->A message -> u. ema_const shuffle is a no-op by construction (all items get one vector).

| arm | direction | seeds | real | off | shuffle | mean-msg | probe | heldout-names real | verdict |
|---|---|---|---|---|---|---|---|---|---|
| none | A->B | 3 | 12.4+-0.7 | n/a | n/a | n/a | n/a | 12.2+-0.4 | baseline |
| none | B->A | 3 | 12.5+-0.1 | n/a | n/a | n/a | n/a | 12.3+-0.7 | baseline |
| ema_const | A->B | 3 | 12.4+-0.7 | 12.4+-0.7 | 12.4+-0.7 | 12.4+-0.7 | 12.1+-0.2 | 12.2+-0.4 | FAIL |
| ema_const | B->A | 3 | 12.5+-0.1 | 12.5+-0.1 | 12.5+-0.1 | 12.5+-0.1 | 12.9+-0.7 | 12.3+-0.7 | FAIL |
| pooled | A->B | 3 | 40.8+-0.2 | 12.5+-0.1 | 11.8+-0.2 | 13.2+-0.6 | 41.1+-0.2 | 40.6+-1.1 | FAIL |
| pooled | B->A | 3 | 100.0+-0.0 | 12.3+-0.5 | 12.8+-0.0 | 12.9+-0.4 | 100.0+-0.0 | 100.0+-0.1 | PASS |
| xattn | A->B | 3 | 23.7+-9.5 | 13.3+-0.5 | 12.7+-0.3 | 12.7+-0.3 | 40.8+-0.4 | 23.0+-9.3 | FAIL |
| xattn | B->A | 3 | 100.0+-0.0 | 12.6+-0.5 | 12.8+-0.0 | 12.4+-0.6 | 100.0+-0.0 | 99.9+-0.1 | PASS |
| slots | A->B | 3 | 20.4+-4.5 | 12.0+-0.1 | 12.3+-0.5 | 12.6+-0.2 | 41.6+-0.7 | 20.6+-4.8 | FAIL |
| slots | B->A | 3 | 100.0+-0.0 | 12.8+-0.5 | 12.8+-0.0 | 12.8+-0.7 | 100.0+-0.0 | 99.3+-0.5 | PASS |

Pass = real >= 90, shuffle <= 16, mean-msg <= 16, probe >= 80 (PREREG.md).

Proved-wrong checks: none triggered.

Total train time (sum over runs): 338.7 min; mean per run 22.6 min.
