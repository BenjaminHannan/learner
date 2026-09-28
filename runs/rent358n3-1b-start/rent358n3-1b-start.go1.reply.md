Mon Sep 28 02:29:07 UTC 2026
job rent358n3-1b-start
slp-358n3 vast start, kit e9e4ba46ae86268361f8fd60e249d9c8cc89a8af, job rent358n3-1b-start, 2026-09-28T02:29:08Z
inputs: 358u loop-s13..16/final.pt sealed on main and matching on the Mac
2026-09-28T02:29:13Z credit $23.73
offers, best TFLOPS per $/h first (id $/h cores host gpu TFLOPS GB waves est_hours):
50741948 0.175 24.0 302304 RTX_3090 35.8 25 1 5.86
44623257 0.401 32.0 213498 RTX_4090 81.4 25 1 2.58
50987217 0.468 18.0 109790 RTX_4090 81.4 25 1 2.58
2026-09-28T02:29:15Z rental 1: instance 53088746 (offer 50741948, host 302304, RTX_3090, 35.8 TFLOPS, 25 GB, 24.0 cores, $0.175/h, 205 TFLOPS per $/h)
launched
2026-09-28T02:34:50Z estimate 5.86 h (1 waves at 25 GB; 5090 104.8 / RTX_3090 35.8 TFLOPS, never below 1x); time cap 31644 s (1.5x); money stop $2.00
2026-09-28T02:34:50Z drive.sh launched on 53088746
2026-09-28T02:34:50Z START
2026-09-28T02:34:50Z HOST nproc 48 disk 40G free; NVIDIA GeForce RTX 3090, 24576 MiB, 580.159.03
2026-09-28T02:36:03Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 3090
2026-09-28T02:36:03Z SEAL 18/18
2026-09-28T02:36:04Z CHECKPOINTS 4/4 (358u loop-s13..16, sha256 as sealed in 358u's SEAL-run)
2026-09-28T02:36:15Z CHECKS-OK
2026-09-28T02:36:33Z SIZES sizes {"sums": 12, "grids": 7} ceiling {"sums": false, "grids": false}
2026-09-28T02:36:33Z RESUME started pid 739 (CPU)
2026-09-28T02:36:33Z LAUNCH s13 pid 752 --long (24071 MiB free before it loads)
2026-09-28T02:37:00Z first seed run launched on 53088746 (the rest start one by one while 5 GB of GPU memory is free); guard started (84164 84166 ); spent so far $0.02
STARTED
rc=0
