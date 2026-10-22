# GPU-RUN-5 readout against PREREG-gpu-run-5.md

**verdict: PASS** — PASS: the defer port goes to code review; defer only in fresh runs from update 0 under new names; no change to 8aB3G2A4/A8

order BDBDBD, complete True, K0 8, window updates 101-300

| trace | kind | updates | window mean loss | started |
|---|---|---|---|---|
| B1 | B | 300 | 2.89402 | 2026-10-20T20:02:43.302176Z |
| D1 | D | 300 | 2.88071 | 2026-10-20T20:10:02.797984Z |
| B2 | B | 300 | 2.86702 | 2026-10-20T20:15:21.645645Z |
| D2 | D | 300 | 2.86362 | 2026-10-20T20:22:06.709932Z |
| B3 | B | 300 | 2.86058 | 2026-10-20T20:27:25.028810Z |
| D3 | D | 300 | 2.87124 | 2026-10-20T20:34:11.172530Z |

| pair | mean abs dloss |
|---|---|
| B1-B2 (B-B) | 0.04812 |
| B1-B3 (B-B) | 0.05871 |
| B2-B3 (B-B) | 0.05558 |
| B1-D1 (B-D) | 0.05263 |
| B1-D2 (B-D) | 0.05541 |
| B1-D3 (B-D) | 0.04327 |
| B2-D1 (B-D) | 0.05046 |
| B2-D2 (B-D) | 0.04757 |
| B2-D3 (B-D) | 0.04486 |
| B3-D1 (B-D) | 0.04972 |
| B3-D2 (B-D) | 0.04840 |
| B3-D3 (B-D) | 0.05208 |

- (i) median AB 0.04972 <= max AA 0.05871: True
- (ii) D window means [2.88071, 2.86362, 2.87124] not all outside the B range [2.86058, 2.89402] on one side: True
- drift proved wrong (every AA < 0.02 and min AB 0.04327 > max AA): False
- at least one B-B pair is >= 0.02: record that 0.02 is too tight for FUTURE B3G2 sheets only (it does not re-judge GPU-RUN-4 or this run)
- information only, not a bar (D-D drift): D1-D2 0.04304, D1-D3 0.04597, D2-D3 0.04302
