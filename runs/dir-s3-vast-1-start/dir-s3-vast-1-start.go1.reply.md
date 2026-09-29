Tue Sep 29 04:52:50 UTC 2026
job dir-s3-vast-1-start
dir-s3 vast start, kit 2e7458d32f0c1ee5d7a164dcd3cf1c1a556e521c, job dir-s3-vast-1-start, 2026-09-29T04:52:52Z
2026-09-29T04:52:55Z credit $22.157552496689306
offers, best TFLOPS per $/h first (id $/h cores host gpu TFLOPS GB waves est_hours):
51737572 0.153 24.0 483833 RTX_3090 35.8 25 1 4.98
51342258 0.388 16.0 103274 RTX_4090 83.0 25 1 2.15
35374381 0.401 32.0 213498 RTX_4090 82.6 25 1 2.16
2026-09-29T04:52:58Z rental 1: instance 53306548 (offer 51737572, host 483833, RTX_3090, 35.8 TFLOPS, 25 GB, 24.0 cores, $0.153/h, 234 TFLOPS per $/h)
2026-09-29T05:01:56Z rental 1: no ssh within 8 min (status loading)
2026-09-29T05:02:09Z DESTROYED 53306548 (confirmed gone), spent so far $0.02
2026-09-29T05:02:10Z rental 2: instance 53307378 (offer 51342258, host 103274, RTX_4090, 83.0 TFLOPS, 25 GB, 16.0 cores, $0.388/h, 214 TFLOPS per $/h)
launched
2026-09-29T05:06:43Z estimate 2.15 h (1 waves at 25 GB; 5090 104.8 / RTX_4090 83.0 TFLOPS, never below 1x); time cap 11609 s (1.5x); money stop $2.50
2026-09-29T05:06:43Z drive.sh launched on 53307378
2026-09-29T05:06:43Z START
2026-09-29T05:06:43Z HOST nproc 1 disk 40G free; NVIDIA GeForce RTX 4090, 24564 MiB, 580.95.05
2026-09-29T05:07:55Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 4090
2026-09-29T05:07:55Z FAILED seal 18/20 3/3 3/3
2026-09-29T05:08:20Z STOPPED: drive.sh did not launch the runs (last: 2026-09-29T05:07:55Z FAILED seal 18/20 3/3 3/3)
2026-09-29T05:08:23Z COPY-CHECK: 7 of 7 files arrived and match the rental's manifest
2026-09-29T05:08:37Z DESTROYED 53307378 (confirmed gone), spent so far $0.07
2026-09-29T05:08:37Z END START-FAIL
rc=0
