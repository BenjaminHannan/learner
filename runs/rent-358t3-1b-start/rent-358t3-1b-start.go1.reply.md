Sun Sep 27 18:36:48 UTC 2026
job rent-358t3-1b-start
rsn-358t v3 vast start, kit 4f7c8a974d47800dc1385387b5c4e79f0a7f5abc, job rent-358t3-1b-start, 2026-09-27T18:36:50Z
RETRY: the earlier start ended HOST-FAIL with every rental ended; its record is kept at /Users/ben-hannan/premonition-watch/rsn358t3-vast.hostfail-*
2026-09-27T18:36:58Z credit $27.67
offers, best TFLOPS per $/h first (id $/h cores host gpu TFLOPS GB waves est_hours):
48293175 0.415 27.428571428571427 124072 RTX_4090 81.4 49 1 2.58
50849759 0.601 64.0 80586 RTX_5090 108.1 33 1 2.0
52597412 0.534 48.0 366851 RTX_6000Ada 81.4 49 1 2.58
2026-09-27T18:37:04Z rental 1: instance 53011267 (offer 48293175, host 124072, RTX_4090, 81.4 TFLOPS, 49 GB, 27.428571428571427 cores, $0.415/h, 196 TFLOPS per $/h)
2026-09-27T18:45:53Z rental 1: no ssh within 8 min (status loading)
2026-09-27T18:46:05Z DESTROYED 53011267 (confirmed gone), spent so far $0.06
2026-09-27T18:46:05Z rental 2: instance 53012679 (offer 50849759, host 80586, RTX_5090, 108.1 TFLOPS, 33 GB, 64.0 cores, $0.601/h, 180 TFLOPS per $/h)
launched
2026-09-27T18:50:43Z estimate 2.0 h (1 waves at 33 GB; 5090 104.8 / RTX_5090 108.1 TFLOPS, never below 1x); time cap 10800 s (1.5x); money stop $2.40
2026-09-27T18:50:43Z drive.sh launched on 53012679
2026-09-27T18:50:43Z START
2026-09-27T18:50:43Z HOST nproc 512 disk 40G free; NVIDIA GeForce RTX 5090, 32607 MiB, 575.57.08
2026-09-27T18:51:56Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090
2026-09-27T18:51:56Z SEAL 22/22
2026-09-27T18:53:15Z FAILED selftest/check-mask/audit (see W/checks.txt)
2026-09-27T18:53:19Z STOPPED: drive.sh did not launch the first run (last: 2026-09-27T18:53:15Z FAILED selftest/check-mask/audit (see W/checks.txt))
2026-09-27T18:53:20Z COPY-CHECK: 5 of 5 files arrived and match the rental's manifest
2026-09-27T18:53:32Z DESTROYED 53012679 (confirmed gone), spent so far $0.14
2026-09-27T18:53:32Z END START-FAIL
rc=0
