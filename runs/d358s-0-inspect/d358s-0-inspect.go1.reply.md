Mon Sep 28 21:33:37 UTC 2026
== END: END DONE spent 1.50
== rentals.txt (id $/h created gone):
52973474 0.469 1790521018 1790532512
== guard processes: 
== last 25 lines of /Users/ben-hannan/premonition-watch/rsn358s-vast/log.txt:
2026-09-27T17:03:30Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 326340 | gpu 96% | spent $0.99
2026-09-27T17:08:32Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 341476 | gpu 96% | spent $1.03
2026-09-27T17:13:37Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 355522 | gpu 96% | spent $1.07
2026-09-27T17:18:40Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 371102 | gpu 96% | spent $1.11
2026-09-27T17:23:44Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 384404 | gpu 96% | spent $1.15
2026-09-27T17:28:47Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 398980 | gpu 95% | spent $1.19
2026-09-27T17:33:54Z ok: 2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0 | bytes 415046 | gpu 96% | spent $1.23
2026-09-27T17:38:58Z ok: 2026-09-27T17:37:33Z TRAIN-EXIT pid 718 rc 0 | bytes 431248 | gpu 96% | spent $1.27
2026-09-27T17:44:02Z ok: 2026-09-27T17:37:33Z TRAIN-EXIT pid 718 rc 0 | bytes 447248 | gpu 96% | spent $1.31
2026-09-27T17:49:06Z ok: 2026-09-27T17:37:33Z TRAIN-EXIT pid 718 rc 0 | bytes 465276 | gpu 87% | spent $1.35
2026-09-27T17:54:09Z ok: 2026-09-27T17:53:24Z TRAIN-EXIT pid 1038 rc 0 | bytes 486491 | gpu 13% | spent $1.38
2026-09-27T17:59:12Z ok: 2026-09-27T17:53:24Z TRAIN-EXIT pid 1038 rc 0 | bytes 503865 | gpu 57% | spent $1.42
2026-09-27T18:04:15Z GUARD DONE
2026-09-27T18:08:17Z COPY-CHECK: 63 of 63 files arrived and match the rental's manifest
2026-09-27T18:08:18Z loop-s9/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:18Z plain-s9/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:18Z loop-s10/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:19Z plain-s10/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:19Z loop-s11/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:19Z plain-s11/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:19Z loop-s12/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:20Z plain-s12/final.pt: sealed, Mac copy sha256 ok
2026-09-27T18:08:20Z COPY-CHECK: all 8 runs accounted for
2026-09-27T18:08:32Z DESTROYED 52973474 (confirmed gone), spent so far $1.50
2026-09-27T18:08:32Z GUARD-END DONE, spent $1.50
== rental progress file (drive-state.txt):
2026-09-27T14:59:48Z START
2026-09-27T14:59:48Z HOST nproc 16 disk 40G free; NVIDIA GeForce RTX 5090, 32607 MiB, 580.105.08
2026-09-27T15:01:02Z TORCH torch 2.11.0+cu128 12.8 True NVIDIA GeForce RTX 5090
2026-09-27T15:01:02Z SEAL 19/19
2026-09-27T15:01:04Z CHECKS-OK
2026-09-27T15:01:05Z LAUNCH loop-s9 pid 537 (32109 MiB free before it loads)
2026-09-27T15:06:05Z LAUNCH plain-s9 pid 638 (26300 MiB free before it loads)
2026-09-27T15:11:05Z LAUNCH loop-s10 pid 718 (23889 MiB free before it loads)
2026-09-27T15:16:05Z LAUNCH plain-s10 pid 798 (17458 MiB free before it loads)
2026-09-27T15:21:05Z LAUNCH loop-s11 pid 878 (14612 MiB free before it loads)
2026-09-27T15:26:05Z LAUNCH plain-s11 pid 958 (9005 MiB free before it loads)
2026-09-27T15:31:05Z LAUNCH loop-s12 pid 1038 (6614 MiB free before it loads)
2026-09-27T15:36:05Z WAIT plain-s12: 624 MiB free
2026-09-27T16:56:06Z LAUNCH plain-s12 pid 2372 (6428 MiB free before it loads)
2026-09-27T17:01:06Z TRAIN-EXIT pid 537 rc 0
2026-09-27T17:37:33Z TRAIN-EXIT pid 638 rc 0
2026-09-27T17:37:33Z TRAIN-EXIT pid 718 rc 0
2026-09-27T17:50:45Z TRAIN-EXIT pid 798 rc 0
2026-09-27T17:50:45Z TRAIN-EXIT pid 878 rc 0
2026-09-27T17:53:24Z TRAIN-EXIT pid 958 rc 0
2026-09-27T17:53:24Z TRAIN-EXIT pid 1038 rc 0
2026-09-27T18:01:51Z TRAIN-EXIT pid 2372 rc 0
2026-09-27T18:01:51Z SEALED loop-s9
2026-09-27T18:01:51Z SEALED plain-s9
2026-09-27T18:01:52Z SEALED loop-s10
2026-09-27T18:01:52Z SEALED plain-s10
2026-09-27T18:01:52Z SEALED loop-s11
2026-09-27T18:01:52Z SEALED plain-s11
2026-09-27T18:01:52Z SEALED loop-s12
2026-09-27T18:01:52Z SEALED plain-s12
2026-09-27T18:01:56Z EVAL plain-s9 rc 0
2026-09-27T18:01:56Z EVAL plain-s10 rc 0
2026-09-27T18:01:56Z EVAL plain-s11 rc 0
2026-09-27T18:01:57Z EVAL plain-s12 rc 0
2026-09-27T18:02:17Z EVAL loop-s12 rc 0
2026-09-27T18:02:17Z EVAL loop-s11 rc 0
2026-09-27T18:02:17Z EVAL loop-s9 rc 0
2026-09-27T18:02:17Z EVAL loop-s10 rc 0
2026-09-27T18:02:17Z DONE
== SEAL-run on the rental (sha and name only):
4d5f54e22e7db0d15519888ed0c688ce0a1c3facd12572e36eba207ef151baef  loop-s9/final.pt
f8cf159a68379bd6a8ce23f6d0da68abb3b8e531fb99a4359f084c9fc11eeb8a  plain-s9/final.pt
dd4f3a3e0bd5ed710b23c9bd546686de959d12f7f63a83a328e2687970b7ff43  loop-s10/final.pt
2a2bea0d2d108346d83be2148e38999bf8c04e685306bcfe4f63569536ab53ce  plain-s10/final.pt
3dc952cbc967b32982951c0e7887854ad7174a4abebeea16ea1213ae7381cacd  loop-s11/final.pt
1ca9257ac1710a838d8844dfa57777c7050b4f5752e320d5ebb068e70a2b841c  plain-s11/final.pt
eed6c14f68cd5b74ec2da4b15503659971c99c6504ed66329dc54081b2aec1c1  loop-s12/final.pt
184a9b7f610c9416402cf7aa7c5d7fa9d3da99372dd13160412a76e02a501128  plain-s12/final.pt
== manifest lines: 63
== per run: final.pt on Mac / train_log / train_summary / tests.json present (yes or no only)
loop-s9: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
plain-s9: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
loop-s10: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
plain-s10: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
loop-s11: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
plain-s11: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
loop-s12: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
plain-s12: sealed=yes mac-copy-matches-seal=yes train_log=yes summary=yes tests=yes
== live vast instances (id label status $/h):
52755827 claude-director-depot exited 0.114
53185848 claude-reading-lis320-codex-20260927 exited 0.494
== collected on main (run-vast/COLLECT.txt in origin/main): no
Mon Sep 28 21:33:42 UTC 2026
rc=0
