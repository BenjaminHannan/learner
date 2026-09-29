Tue Sep 29 06:55:27 UTC 2026
job dir-s3-vast-1-start-r2
dir-s3 vast start, kit fc64d12fc2d22dd3b699889dfff32d67017c7055, job dir-s3-vast-1-start-r2, 2026-09-29T06:55:29Z
RETRY: the earlier start ended START-FAIL with every rental ended; its record is kept at /Users/ben-hannan/premonition-watch/dirs3-vast.startfail-*
2026-09-29T06:55:32Z credit $22.049226792989245
offers, best TFLOPS per $/h first (id $/h cores host gpu TFLOPS GB waves est_hours):
36295187 0.161 64.0 86812 RTX_3090 35.3 25 1 5.05
51500792 0.484 32.0 366851 RTX_4090 81.4 25 1 2.19
52963860 0.601 64.0 88910 RTX_4090 81.4 25 1 2.19
2026-09-29T06:55:35Z rental 1: instance 53319683 (offer 36295187, host 86812, RTX_3090, 35.3 TFLOPS, 25 GB, 64.0 cores, $0.161/h, 219 TFLOPS per $/h)
launched
2026-09-29T06:58:02Z estimate 5.05 h (1 waves at 25 GB; 5090 104.8 / RTX_3090 35.3 TFLOPS, never below 1x); time cap 27269 s (1.5x); money stop $2.50
2026-09-29T06:58:02Z drive.sh launched on 53319683
2026-09-29T06:58:02Z START
2026-09-29T06:58:02Z HOST nproc 64 disk 40G free; NVIDIA GeForce RTX 3090, 24576 MiB, 595.71.05
2026-09-29T06:59:21Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 3090
2026-09-29T06:59:21Z SEAL 20/20 3/3 3/3
2026-09-29T07:08:09Z CHECKS-OK
2026-09-29T07:08:13Z STAGE0-OK
2026-09-29T07:08:13Z LAUNCH min-loop-s13 pid 720
2026-09-29T07:08:13Z LAUNCH min-plain-s13 pid 724
2026-09-29T07:08:13Z LAUNCH min-loop-s14 pid 728
2026-09-29T07:08:13Z LAUNCH min-plain-s14 pid 730
2026-09-29T07:08:13Z LAUNCH random-loop-s13 pid 732
2026-09-29T07:08:13Z LAUNCH random-plain-s13 pid 734
2026-09-29T07:08:13Z LAUNCH random-loop-s14 pid 736
2026-09-29T07:08:13Z LAUNCH random-plain-s14 pid 738
2026-09-29T07:08:13Z LAUNCHED-ALL
2026-09-29T07:08:47Z all 8 nets launched on 53319683; guard started (4931 4933 ); spent so far $0.04
STARTED
rc=0
