14:42:50 start rent-rv390b-p1 (BASH-ONLY rental, no builder); code f5213af7c75577b494a22cc8ea05715258db770f; steps: A C D; test mode: 0
14:43:00 vast credit, balance: 32.67767178383956 0
14:43:00 Mac nets (/Users/ben-hannan/premonition-models/rsn358i2): seeds 1 2 3 4 match
14:43:04 offers read 64; kept 19; dropped: over $1.20/h 26, under 16 GB GPU RAM 0, compute capability under 7.5 0, too slow for this job 19
14:43:04 best offers (id, $/h, card, TFLOPS, TFLOPS per $/h, slowdown vs RTX 5090, estimated step minutes):
42213651 0.4014 RTX_4090 81.4 202.8 1.288 28.3
51466240 0.5536 RTX_5090 111.8 201.9 1.0 22.0
52775598 0.4285 RTX_4090 81.4 189.9 1.288 28.3
48470917 0.4412 RTX_4090 81.4 184.5 1.288 28.3
14:43:06 created instance 52971329 on offer 42213651: card RTX_4090, 81.4 TFLOPS, $0.4014/h (202.8 TFLOPS per $/h), estimated 28.3 step minutes; label claude-thought-rv390b-p1
14:43:52 ssh ok: instance 52971329
14:43:56 image torch: 2.8.0+cu128
14:43:56 installing torch 2.11.0 (cu128 wheels), in the foreground (try 1)
pip-rc=0
torchvision 0.23.0+cu128 requires torch==2.8.0, but you have torch 2.11.0+cu128 which is incompatible.
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
14:44:58 torchok 2.11.0+cu128 12.8 True
14:45:29 code tree sent (rc 0)
14:47:31 nets on the rental match NETS-358i2: seeds 1 2 3 4
14:47:34 job scripts sent (rc 0)
seal artifacts/claude-rv390-20260926/SEAL.sha256.txt 15 15
seal artifacts/claude-rv392-20260926/SEAL.sha256.txt 14 14
seal artifacts/claude-rv392-20260926/SEAL-addendum-1.sha256.txt 2 2
r0print untrained loop net /root/work/RAND/loop-r0.pt init seed 0 weights 6438302 weights_sha256 a23da0b8934d07796df1d02a01ad5965ada83e61e280996b95caf4b3d3dc4c74 file_sha256 23c7ca658dac4b8f50d1219fd5d51c35b0a1d7a37f51df927a19b358e121d937
r0file ok
torch 2.11.0+cu128 12.8
gpu NVIDIA GeForce RTX 4090, 595.58.03
14:47:40 seeds: 1 2 3 4; r0 made: 1
14:47:40 step A: start, budget 3082 s
launched
started: s1 s2 s3 s4 r0 | pids: 895 896 897 898 899
s1 rc=0 last: grids7 {"n": 300, "day_right": 195, "unfinished": 105, "day_right_any_round": 216, "hard": 84, "keep": {"solved": 21, "solved_by_48": 21, "solved_after_48": 0, "hard_solved": 0}, "restart": {"solved": 50, "hard_solved": 30}, "guess": {"solved": 71, "solved_by_48": 60, "hard_solved": 50, "guesses": 507}, "interrupt": {"n": 40, "pause_rounds": [217, 292, 333, 445, 475], "keep_identical": true, "keep_pauses": 5, "guess_identical": 40, "guess_puzzles_paused": 11, "messages": 60, "messages_identical": 60, "max_round_sec": 0.2242, "max_pause_sec": 0.0019, "max_wait_sec": 0.2261, "device": "cuda"}, "
s2 rc=0 last: grids7 {"n": 300, "day_right": 255, "unfinished": 45, "day_right_any_round": 264, "hard": 36, "keep": {"solved": 10, "solved_by_48": 9, "solved_after_48": 1, "hard_solved": 1}, "restart": {"solved": 34, "hard_solved": 27}, "guess": {"solved": 13, "solved_by_48": 10, "hard_solved": 4, "guesses": 300}, "interrupt": {"n": 40, "pause_rounds": [217, 292, 333, 445, 475], "keep_identical": true, "keep_pauses": 5, "guess_identical": 40, "guess_puzzles_paused": 28, "messages": 145, "messages_identical": 145, "max_round_sec": 0.2173, "max_pause_sec": 0.0011, "max_wait_sec": 0.2184, "device": "cuda"}, "s
s3 rc=0 last: grids7 {"n": 300, "day_right": 187, "unfinished": 113, "day_right_any_round": 222, "hard": 78, "keep": {"solved": 35, "solved_by_48": 35, "solved_after_48": 0, "hard_solved": 0}, "restart": {"solved": 84, "hard_solved": 49}, "guess": {"solved": 77, "solved_by_48": 52, "hard_solved": 42, "guesses": 747}, "interrupt": {"n": 40, "pause_rounds": [217, 292, 333, 445, 475], "keep_identical": true, "keep_pauses": 5, "guess_identical": 40, "guess_puzzles_paused": 16, "messages": 85, "messages_identical": 85, "max_round_sec": 0.1403, "max_pause_sec": 0.0012, "max_wait_sec": 0.1415, "device": "cuda"}, "
s4 rc=0 last: grids7 {"n": 300, "day_right": 192, "unfinished": 108, "day_right_any_round": 210, "hard": 90, "keep": {"solved": 18, "solved_by_48": 18, "solved_after_48": 0, "hard_solved": 0}, "restart": {"solved": 61, "hard_solved": 43}, "guess": {"solved": 70, "solved_by_48": 47, "hard_solved": 52, "guesses": 676}, "interrupt": {"n": 40, "pause_rounds": [217, 292, 333, 445, 475], "keep_identical": true, "keep_pauses": 5, "guess_identical": 40, "guess_puzzles_paused": 12, "messages": 65, "messages_identical": 65, "max_round_sec": 0.1849, "max_pause_sec": 0.0019, "max_wait_sec": 0.1868, "device": "cuda"}, "
r0 rc=0 last: grids7 {"n": 300, "day_right": 0, "unfinished": 300, "day_right_any_round": 0, "hard": 300, "keep": {"solved": 0, "solved_by_48": 0, "solved_after_48": 0, "hard_solved": 0}, "restart": {"solved": 0, "hard_solved": 0}, "guess": {"solved": 26, "solved_by_48": 0, "hard_solved": 26, "guesses": 6201}, "interrupt": {"n": 40, "pause_rounds": [217, 292, 333, 445, 475], "keep_identical": true, "keep_pauses": 5, "guess_identical": 40, "guess_puzzles_paused": 36, "messages": 185, "messages_identical": 185, "max_round_sec": 0.0099, "max_pause_sec": 0.0012, "max_wait_sec": 0.011, "device": "cuda"}, "sec": 
gpumem A max used MiB: 3947 of 24564
STEP-END A killed=0
15:08:05 step A: about 20 min
15:08:08 step A: copy 1: 25 files here, manifest 25, sha256 OK 25
15:08:08 step A: delivered (25 files)
15:08:08 step C: start, budget 1459 s
launched
started: s1 s2 s3 s4 | pids: 2656 2657 2658 2659
s1 rc=0 last: p-grids6 {"guesses": 17, "wrong": 3, "first_guesses": 5, "all": {"dq": 0.4762, "d_mean_ent": 0.6667, "d_max_ent": 0.7857, "flips": 0.5238, "p_written": 0.4048, "clash_rule_based": 0.5714}, "first": {"dq": null, "d_mean_ent": null, "d_max_ent": null, "flips": null, "p_written": null, "clash_rule_based": null}, "unfinished": 6, "solved": 5}
s2 rc=0 last: p-grids6 {"guesses": 25, "wrong": 10, "first_guesses": 4, "all": {"dq": 0.3333, "d_mean_ent": 0.3333, "d_max_ent": 0.4067, "flips": 0.4033, "p_written": 0.3867, "clash_rule_based": 0.44}, "first": {"dq": 0.6667, "d_mean_ent": 0.6667, "d_max_ent": 0.0, "flips": 0.0, "p_written": 0.3333, "clash_rule_based": 0.1667}, "unfinished": 4, "solved": 1}
s3 rc=0 last: p-grids6 {"guesses": 40, "wrong": 8, "first_guesses": 7, "all": {"dq": 0.3789, "d_mean_ent": 0.6172, "d_max_ent": 0.582, "flips": 0.4512, "p_written": 0.332, "clash_rule_based": 0.4922}, "first": {"dq": null, "d_mean_ent": null, "d_max_ent": null, "flips": null, "p_written": null, "clash_rule_based": null}, "unfinished": 12, "solved": 9}
s4 rc=0 last: p-grids6 {"guesses": 32, "wrong": 2, "first_guesses": 9, "all": {"dq": 0.0, "d_mean_ent": 0.3833, "d_max_ent": 0.5667, "flips": 0.5833, "p_written": 0.4, "clash_rule_based": 0.475}, "first": {"dq": null, "d_mean_ent": null, "d_max_ent": null, "flips": null, "p_written": null, "clash_rule_based": null}, "unfinished": 11, "solved": 10}
gpumem C max used MiB: 2962 of 24564
STEP-END C killed=0
15:08:55 step C: about 1 min
15:09:05 step C: copy 1: 12 files here, manifest 12, sha256 OK 12
15:09:05 step C: delivered (12 files)
15:09:05 step D: start, budget 1459 s
launched
started: s1 s2 s3 s4 | pids: 3002 3003 3004 3005
s1 rc=0 last: rv392 grids7 n 300 right 204 hard 83
s2 rc=0 last: rv392 grids7 n 300 right 243 hard 51
s3 rc=0 last: rv392 grids7 n 300 right 191 hard 80
s4 rc=0 last: rv392 grids7 n 300 right 193 hard 83
gpumem D max used MiB: 1 of 24564
STEP-END D killed=0
15:09:30 step D: about 0 min
15:09:34 step D: copy 1: 12 files here, manifest 12, sha256 OK 12
15:09:34 step D: delivered (12 files)
RESULT: delivered steps: A C D; not run or incomplete: none; seeds: 1 2 3 4; r0 made: 1; instance kept stopped: 0
15:09:34 destroying instance 52971329 (this job created it)
15:09:46 instance 52971329 gone
LEDGER: 2026-09-27 15:09:46 UTC Memory for its own thoughts: rent-rv390b-p1, vast instance 52971329 (RTX_4090, 81.4 TFLOPS, at $0.4014/h) for 27 min = about $0.18 (dph x minutes since create; the Director's ledger is the record)
rc=0
