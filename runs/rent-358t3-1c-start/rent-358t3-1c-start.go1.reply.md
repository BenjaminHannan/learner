Sun Sep 27 19:28:18 UTC 2026
job rent-358t3-1c-start
rsn-358t v3 vast start, kit 7a1e0b85ee79ea9febca00ae5fdcd91a7bd1312e, job rent-358t3-1c-start, 2026-09-27T19:28:19Z
RETRY: the earlier start ended START-FAIL with every rental ended; its record is kept at /Users/ben-hannan/premonition-watch/rsn358t3-vast.startfail-*
2026-09-27T19:28:23Z credit $27.58
offers, best TFLOPS per $/h first (id $/h cores host gpu TFLOPS GB waves est_hours):
46151928 0.415 16.0 135676 RTX_4090 81.4 49 1 2.58
47088901 0.561 48.0 24953 RTX_5090 109.1 33 1 2.0
50163305 0.537 48.0 366851 RTX_6000Ada 81.4 49 1 2.58
2026-09-27T19:28:25Z rental 1: instance 53019496 (offer 46151928, host 135676, RTX_4090, 81.4 TFLOPS, 49 GB, 16.0 cores, $0.415/h, 196 TFLOPS per $/h)
launched
2026-09-27T19:30:48Z estimate 2.58 h (1 waves at 49 GB; 5090 104.8 / RTX_4090 81.4 TFLOPS, never below 1x); time cap 13932 s (1.5x); money stop $2.40
2026-09-27T19:30:48Z drive.sh launched on 53019496
2026-09-27T19:30:48Z START
2026-09-27T19:30:48Z HOST nproc 128 disk 40G free; NVIDIA GeForce RTX 4090, 49140 MiB, 595.71.05
2026-09-27T19:35:29Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 4090
2026-09-27T19:35:29Z SEAL 22/22
2026-09-27T19:36:06Z CHECKS-OK
2026-09-27T19:36:09Z STAGE0-OK
2026-09-27T19:36:09Z LAUNCH loop-trm-s1 pid 1343 (48496 MiB free before it loads)
2026-09-27T19:36:31Z first run launched on 53019496 (the rest start one by one while 5 GB of GPU memory is free); guard started (63996 63998 ); spent so far $0.06
STARTED
rc=0
