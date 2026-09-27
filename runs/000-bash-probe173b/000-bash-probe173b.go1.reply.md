10:56:54 start 000-bash-probe173b (BASH-ONLY, no builder); origin/main bc89fbd38; steps: T1 T2; test mode: 1
10:56:55 marker: BUSY: queue job 158-claude-sleep-358spc-finish since 2026-09-27T09:42:53Z - do not use this GPU until this file is gone 
332
INFO: No tasks are running which match the specified criteria.
rc=0
FOLDER-ABSENT
10:57:03 C: free bytes: 4389736448
10:59:57 code tree extracted (ssh rc 0)
10:59:57 job scripts copied (ssh rc 0)
seal artifacts/claude-rv390-20260926/SEAL.sha256.txt 15 15
seal artifacts/claude-rv392-20260926/SEAL.sha256.txt 14 14
seal artifacts/claude-rv392-20260926/SEAL-addendum-1.sha256.txt 2 2
net s1 d30887c59f57496a1a195d7250e130bb1c51393d973ce45f4bdd898ba5eb8261
net s2 4085df22366b96190b087a7b46333daec9f19d078332ea5bf6328a15f2ed6594
net s3 5d571cc276d88f5af5da34c79e0d198878f9e674888b2150107095e27adc4a7a
net s4 f0a84b11d1722d97739a5999f3b2b487c0bc09dc1c927fde14e6566adedd6621
r0print untrained loop net C:/Users/benja/probe173c/RAND/loop-r0.pt init seed 0 weights 6438302 weights_sha256 518b6be03bec73bd4c2e8b9b83a8dc346113f624686a8b66f538cad7d1f020a3 file_sha256 5048fa09b3cf820e8f3a7a9125e7cccdac16bef8cca90daca1bd3a436b97eb10
r0file ok
torch 2.11.0+cu128 12.8
gpu NVIDIA GeForce RTX 5070 Ti, 591.86
11:00:04 seeds: 1 2 3 4; r0 made: 1
11:00:04 step T1: start, budget 120 s
started: s1 s2 s3 s4 r0 | msys: 1002 1003 1004 1005 1006 | win:      | python.exe now 0
s1 rc=0 last: sleeper T1 slept 3
s2 rc=0 last: sleeper T1 slept 3
s3 rc=0 last: sleeper T1 slept 3
s4 rc=0 last: sleeper T1 slept 3
r0 rc=0 last: sleeper T1 slept 3
python.exe after step: 0
STEP-END T1 killed=0
11:00:14 step T1: about 0 min
11:00:15 step T1: copied back (10 files)
11:00:15 step T2: start, budget 30 s
started: s1 s2 s3 s4 r0 | msys: 831 832 833 834 835 | win:  7060 17708 8760 19708 | python.exe now 8
DEADLINE: 4 runs still going; stopping this step's own runs by exact PID (process tree)
SUCCESS: The process with PID 3580 (child process of PID 7060) has been terminated.
SUCCESS: The process with PID 7060 (child process of PID 2648) has been terminated.
SUCCESS: The process with PID 24336 (child process of PID 17708) has been terminated.
SUCCESS: The process with PID 17708 (child process of PID 14044) has been terminated.
SUCCESS: The process with PID 23540 (child process of PID 8760) has been terminated.
SUCCESS: The process with PID 8760 (child process of PID 8332) has been terminated.
SUCCESS: The process with PID 8600 (child process of PID 19708) has been terminated.
SUCCESS: The process with PID 19708 (child process of PID 16184) has been terminated.
s1 rc=0 last: sleeper T2 slept 3
s2 rc=1 last: 
s3 rc=1 last: 
s4 rc=1 last: 
r0 rc=1 last: 
python.exe after step: 0
STEP-END T2 killed=1
11:00:55 step T2: about 1 min
11:00:55 step T2: incomplete (deadline, error or ssh loss); its partial output is not copied
11:00:55 removing C:\Users\benja\probe173c
GONE
--- test copy:
copy/probe/T1/log-s3.txt
copy/probe/T1/log-s2.txt
copy/probe/T1/log-s1.txt
copy/probe/T1/log-s4.txt
copy/probe/T1/log-r0.txt
copy/probe/T1/SOURCES.txt
copy/probe/T1/out-s3.txt
copy/probe/T1/out-s2.txt
copy/probe/T1/out-s1.txt
copy/probe/T1/out-r0.txt
copy/probe/T1/out-s4.txt
000-bash-probe173b sources (BASH-ONLY job, no builder; step T1; written 2026-09-27T11:00:15Z)
BensPC GPU: NVIDIA GeForce RTX 5070 Ti, 591.86
python torch CUDA: torch 2.11.0+cu128 12.8
loop-s1: C:/Users/benja/premonition-models/rsn358i2/loop-s1/final.pt sha256 d30887c59f57496a1a195d7250e130bb1c51393d973ce45f4bdd898ba5eb8261 (matches NETS-358i2.sha256.txt)
loop-s2: C:/Users/benja/premonition-models/rsn358i2/loop-s2/final.pt sha256 4085df22366b96190b087a7b46333daec9f19d078332ea5bf6328a15f2ed6594 (matches NETS-358i2.sha256.txt)
loop-s3: C:/Users/benja/premonition-models/rsn358i2/loop-s3/final.pt sha256 5d571cc276d88f5af5da34c79e0d198878f9e674888b2150107095e27adc4a7a (matches NETS-358i2.sha256.txt)
loop-s4: C:/Users/benja/premonition-models/rsn358i2/loop-s4/final.pt sha256 f0a84b11d1722d97739a5999f3b2b487c0bc09dc1c927fde14e6566adedd6621 (matches NETS-358i2.sha256.txt)
r0 (untrained control, never pushed): untrained loop net C:/Users/benja/probe173c/RAND/loop-r0.pt init seed 0 weights 6438302 weights_sha256 518b6be03bec73bd4c2e8b9b83a8dc346113f624686a8b66f538cad7d1f020a3 file_sha256 5048fa09b3cf820e8f3a7a9125e7cccdac16bef8cca90daca1bd3a436b97eb10
minutes for step T1: 0
RESULT: delivered steps: T1; not run or incomplete: T2; seeds: 1 2 3 4; r0 made: 1
probe173-tar GONE
probe173-tmp GONE
python.exe at end: 0
Sun Sep 27 11:01:02 UTC 2026
rc=0
