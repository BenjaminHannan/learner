# GPU-RUN-4 booking (2026-10-20)

Under PREREG-launch-defer.md (sealed 10-17) and the coordinator's granted spend (~$1.8 expected, $2.07 max). Booked with Ben's go-ahead in-session (10-20) after the permission check stopped the first attempt (10-17).

| box | part | Vast instance | offer | host | CPU | dph_total | MAXH | ceiling | created (UTC) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | full | 56810922 | 51840647 | machine 151645 / host 655981, Quebec CA | Xeon Platinum 8352V | $0.4430 | 3 h | $1.33 | 2026-10-20T00:15:21Z |
| 2 | rep | 56810924 | 56341697 | machine 150319 / host 366851, California US | AMD EPYC 9684X | $0.4593 | 1.5 h | $0.69 | 2026-10-20T00:15:21Z |

Total ceiling $2.02 (inside $2.07). Credit before booking: $22.21 (no instance of this session running; six exited RTX 3090 instances of another session listed, not touched).
Box script `gpu_run_4_box.sh` sha256 ff2563410e2182f7cf2798c395737bfeb40b52c4eb08650f3d463bd66292cd40, commit ad33f572; image pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime (kit vast.py b68462f7...).
