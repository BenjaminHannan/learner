# GPU-RUN-4 booking (2026-10-20)

Under PREREG-launch-defer.md (sealed 10-17) and the coordinator's granted spend (~$1.8 expected, $2.07 max). Booked with Ben's go-ahead in-session (10-20) after the permission check stopped the first attempt (10-17).

| box | part | Vast instance | offer | host | CPU | dph_total | MAXH | ceiling | created (UTC) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | full | 56810922 | 51840647 | machine 151645 / host 655981, Quebec CA | Xeon Platinum 8352V | $0.4430 | 3 h | $1.33 | 2026-10-20T00:15:21Z |
| 2 | rep | 56810924 | 56341697 | machine 150319 / host 366851, California US | AMD EPYC 9684X | $0.4593 | 1.5 h | $0.69 | 2026-10-20T00:15:21Z |

Total ceiling $2.02 (inside $2.07). Credit before booking: $22.21 (no instance of this session running; six exited RTX 3090 instances of another session listed, not touched).
Box script `gpu_run_4_box.sh` sha256 ff2563410e2182f7cf2798c395737bfeb40b52c4eb08650f3d463bd66292cd40, commit ad33f572; image pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime (kit vast.py b68462f7...).

## Billed rate above the offer price (10-20 00:16Z, read from `status`)
Box 1 bills **$0.4696/h** (offer $0.4430) and box 2 bills **$0.5126/h** (offer $0.4593). This is the gap GPU-RUN-3 hit too (PREREG-b3g2-speed-ab Amendment 3.4). The box scripts' guard and dollar lines use the DPH given at creation, so every dollar figure in the readout is recomputed as wall time × the billed rate.

At the billed rates, the MAXH worst case would be 3 × 0.4696 + 1.5 × 0.5126 = $2.18, above the granted $2.07. Hard destroy deadlines hold the worst case at $2.07:
- box 2 is destroyed no later than **01:32:40Z** (1.29 h × 0.5126 = $0.66);
- box 1 is destroyed no later than its MAXH, **03:15:21Z** (3 h × 0.4696 = $1.41).

Expected: box 1 about 2.1 h ($0.99), box 2 about 1.1 h ($0.56), about $1.55 in all.
