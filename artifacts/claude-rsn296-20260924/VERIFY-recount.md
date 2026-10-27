# rsn-296 recount from files (reasoning thread, 2026-09-24; source reeval-cpu/ on builder-outbox)

A CPU re-eval of all 8 kept checkpoints restored the panel JSONs. All 8 checkpoints matched the run seal. I recounted from the JSONs myself.

**Verdict: 296 = registered FAIL on P296.4 only.** P296.1, P296.2 and P296.3 all PASS on both plain seeds.

| mark | bar | plain s1 | plain s2 |
|---|---|---|---|
| P296.1 invented (checked, after the fact-check) | ≤2 each panel | fresh 0 and transfer 0, PASS | fresh 0 and transfer 0, PASS |
| P296.2 transfer | ≥204 / ≥209 | 238, PASS | 238, PASS |
| P296.3 fresh code-doable | ≥168/178 | 173, PASS | 169, PASS |
| P296.4 fresh total | ≥228/298 | 225, FAIL | 217, FAIL |

- The builder's "5 and 6 invented" were the RAW counts, from before the fact-check (raw 5 and 6 on the fresh finals). The fact-check turned every one of them into "I don't know". P296.1 is scored on checked answers, as P294.1 was.
- Every final-checkpoint total matches RESULTS.md exactly. One copy-only file differs by 1: plain-s1 on panel294, 194 on the CPU vs 195 on the GPU. It doesn't touch any mark.
- The loop arms had 0 checked inventions. Their finals were fresh 106 and 101, transfer 89 and 87.
