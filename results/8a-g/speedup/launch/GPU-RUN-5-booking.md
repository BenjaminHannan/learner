# GPU-RUN-5 booking (2026-10-20)

Under PREREG-gpu-run-5.md (sealed 10-20, sha256 0ab5dbfd…708d; the coordinator accepted the seal as filed). Booked after Ben's own approval in this session ("Yes, you can do it", 10-20, in reply to the request for "Coordinator approves GPU-RUN-5").

| Vast instance | offer | host | CPU | offer dph | billed dph | MAXH | created (UTC) |
|---|---|---|---|---|---|---|---|
| 56940993 | 18138401 | machine 9204 / host 34742, Utah US | AMD EPYC 7C13 | $0.4563 | **$0.4830** | 1.75 h | 2026-10-20T19:32:51Z |

The first offer picked (41245400, Texas) was gone at create time ("no_such_ask"), and nothing was created there.

Hard cap $1.00 billed: 1.00 / 0.4830 = 2.07 h, so the box is destroyed **no later than 21:36Z**. MAXH alone ends the script by 21:18Z (+5 min sleep). Expected: about 70 min, about $0.56.

Box script `gpu_run_5_box.sh` sha256 3448698a…be1e (commit 9f9e4107), readout `gpu_run_5_marks.py` sha256 9e281cba…f346. Credit before booking: $17.98.
