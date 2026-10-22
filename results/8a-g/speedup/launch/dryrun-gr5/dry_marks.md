# GPU-RUN-5 readout against PREREG-gpu-run-5.md

**verdict: FAIL** — FAIL, and "it is just drift" is proved wrong: every AA < 0.02 and every AB > every AA. defer is closed for good

order BDBDBD, complete True, K0 8, window updates 101-300

| trace | kind | updates | window mean loss | started |
|---|---|---|---|---|
| B1 | B | 300 | 7.47877 | 2026-10-20T02:29:24.222986Z |
| D1 | D | 300 | 7.47276 | 2026-10-20T02:31:13.338558Z |
| B2 | B | 300 | 7.47877 | 2026-10-20T02:32:24.899910Z |
| D2 | D | 300 | 7.48009 | 2026-10-20T02:34:08.577030Z |
| B3 | B | 300 | 7.47877 | 2026-10-20T02:35:19.044693Z |
| D3 | D | 300 | 7.46750 | 2026-10-20T02:37:08.187129Z |

| pair | mean abs dloss |
|---|---|
| B1-B2 (B-B) | 0.00000 |
| B1-B3 (B-B) | 0.00000 |
| B2-B3 (B-B) | 0.00000 |
| B1-D1 (B-D) | 0.01813 |
| B1-D2 (B-D) | 0.01429 |
| B1-D3 (B-D) | 0.01823 |
| B2-D1 (B-D) | 0.01813 |
| B2-D2 (B-D) | 0.01429 |
| B2-D3 (B-D) | 0.01823 |
| B3-D1 (B-D) | 0.01813 |
| B3-D2 (B-D) | 0.01429 |
| B3-D3 (B-D) | 0.01823 |

- (i) median AB 0.01813 <= max AA 0.00000: False
- (ii) D window means [7.47276, 7.48009, 7.4675] not all outside the B range [7.47877, 7.47877] on one side: True
- drift proved wrong (every AA < 0.02 and min AB 0.01429 > max AA): True
- every B-B pair < 0.02
- information only, not a bar (D-D drift): D1-D2 0.01932, D1-D3 0.01907, D2-D3 0.01927
