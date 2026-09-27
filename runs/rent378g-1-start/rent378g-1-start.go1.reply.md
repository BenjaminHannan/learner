Sun Sep 27 14:59:10 UTC 2026
job rent378g-1-start
rd-378g vast start, kit 54cfbbfcb2def18f121297dd833869e6e07f9e1f, job rent378g-1-start, 2026-09-27T14:59:15Z
2026-09-27T14:59:18Z credit $32.0
2026-09-27T14:59:18Z R on the Mac: present (/Users/ben-hannan/premonition-models/rd378-notes-merged); rsend.sh checks its sha256
2026-09-27T14:59:19Z offers read 64; kept 49; dropped: over $1.00/h 8, under 16000 MB GPU RAM 0, compute capability under 800 0, CUDA under 12.8 0, estimate over 0.8 x $2.50 7
best offers (id $/h host card TFLOPS GPU-RAM-MB TFLOPS-per-$/h slowdown-vs-5090 estimated-$):
49250868 0.508 371998 RTX_5090 107.6 32607 211.8 1.0 0.51
43165155 0.513 410852 RTX_5090 108.1 32607 210.9 1.0 0.51
36865802 0.401 213498 RTX_4090 81.4 24564 202.8 1.288 0.52
2026-09-27T14:59:20Z CARD rental 1: instance 52973785 (offer 49250868, host 371998): RTX_5090, 107.6 TFLOPS, 32607 MB GPU RAM, $0.508/h, 211.8 TFLOPS per $/h, slowdown vs 5090 x1.0, estimate $0.51
2026-09-27T15:08:27Z rental 1: no ssh within 8 min (status loading)
2026-09-27T15:08:40Z DESTROYED 52973785 (confirmed gone), spent so far $0.08
2026-09-27T15:08:42Z CARD rental 2: instance 52975125 (offer 43165155, host 410852): RTX_5090, 108.1 TFLOPS, 32607 MB GPU RAM, $0.513/h, 210.9 TFLOPS per $/h, slowdown vs 5090 x1.0, estimate $0.51
launched
2026-09-27T15:11:11Z time cap 15600 s (3 x 60 min x slowdown 1.0 x 1 wave(s) + 60 min for R + 20 min setup); money stop $2.50
2026-09-27T15:11:11Z drive.sh launched on 52975125
2026-09-27T15:11:11Z START
2026-09-27T15:11:11Z HOST nproc 256 disk 40G free; GPU NVIDIA GeForce RTX 5090, 32607, 580.159.03, 12.0
2026-09-27T15:25:29Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090 transformers 5.17.0 peft 0.21.0 torchvision None
2026-09-27T15:26:57Z BASE /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc; MINILM ok
2026-09-27T15:27:07Z SEALS and 4 selftests ok
2026-09-27T15:27:15Z DATA ok
2026-09-27T15:27:59Z training started on 52975125; guard started (99343 99355 99382 ); spent so far $0.24
STARTED
rc=0
