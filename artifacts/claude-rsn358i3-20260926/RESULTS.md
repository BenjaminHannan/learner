# rsn-358i3 results: fixed 358i loop vs plain twin, fresh seeds 5-8, both on BensPC (builder claude-sleep-358i3pc, 2026-09-26/27)

## Verdict: PASS

V0 validity: PASS. steps_block_nograd = 0 in every loop train_summary.json (loop-s5 0, loop-s6 0, loop-s7 0, loop-s8 0, steps_seen 60000 each).
G0 validity: met 8/8 arms. On every seed s5-s8, loop and plain are right on >= 210/300 of the practised-size tests in 2 of 3 kinds (sums4 300/300 and grids5 298-300/300 on all 8 arms; numbers4 0-5/300 everywhere).
G1 bigger: PASS. 4-seed mean loop-minus-plain: sums6 +124.00 (>= +30), grids6 +52.00 (>= +30), numbers5 +0.00 (>= -10). Per-seed gap > 0 on 4/4 seeds for sums6 and 4/4 for grids6 (>= 3 required).
G2 practised: PASS. 4-seed mean loop-minus-plain: sums4 +0.00, grids5 +1.50, numbers4 +0.75 (all >= -10).
G3 stop: PASS. On 4/4 seeds (>= 3 required), loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test (12/12 checks pass; numbers5: 0 vs fixed16 0/0/1/0). 4-seed mean rounds sums6 7.56 > sums4 6.71 (also per-seed 4/4: 7.57>6.55, 7.85>7.07, 7.16>6.65, 7.67>6.58).
Proved-wrong clause: NOT triggered (requires V0+G0 met and mean loop-minus-plain <= +5 on all three bigger tests; sums6 is +124.00, grids6 is +52.00).

PASS = V0, G0, G1, G2 and G3 all met. "The loop beats its same-size plain twin" is SHOWN for these puzzle kinds at this size, on one machine.

## Per-seed right counts (n=300 each; G = loop minus plain; means over 4 seeds)

| test | L5 | P5 | G5 | L6 | P6 | G6 | L7 | P7 | G7 | L8 | P8 | G8 | meanL | meanP | meanG |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sums4 | 300 | 300 | +0 | 300 | 300 | +0 | 300 | 300 | +0 | 300 | 300 | +0 | 300.00 | 300.00 | +0.00 |
| sums6 | 299 | 218 | +81 | 296 | 125 | +171 | 289 | 179 | +110 | 296 | 162 | +134 | 295.00 | 171.00 | +124.00 |
| sums8 | 282 | 145 | +137 | 268 | 36 | +232 | 237 | 69 | +168 | 275 | 69 | +206 | 265.50 | 79.75 | +185.75 |
| grids5 | 300 | 299 | +1 | 300 | 298 | +2 | 300 | 299 | +1 | 300 | 298 | +2 | 300.00 | 298.50 | +1.50 |
| grids6 | 296 | 248 | +48 | 294 | 241 | +53 | 284 | 234 | +50 | 295 | 238 | +57 | 292.25 | 240.25 | +52.00 |
| grids7 | 242 | 144 | +98 | 214 | 149 | +65 | 174 | 138 | +36 | 218 | 146 | +72 | 212.00 | 144.25 | +67.75 |
| numbers4 | 2 | 1 | +1 | 5 | 1 | +4 | 1 | 2 | -1 | 0 | 1 | -1 | 2.00 | 1.25 | +0.75 |
| numbers5 | 0 | 0 | +0 | 0 | 0 | +0 | 0 | 0 | +0 | 0 | 0 | +0 | 0.00 | 0.00 | +0.00 |
| sums10 | 232 | 105 | +127 | 228 | 12 | +216 | 172 | 56 | +116 | 235 | 51 | +184 | 216.75 | 56.00 | +160.75 |
| sums12 | 178 | 85 | +93 | 183 | 5 | +178 | 133 | 26 | +107 | 176 | 36 | +140 | 167.50 | 38.00 | +129.50 |

Roles: practised = sums4, grids5, numbers4; bigger = sums6, grids6, numbers5; report = sums8, grids7, sums10, sums12.

## Loop fixed rounds (right at 1/2/4/8/12/16/24/32/48 rounds; any = right at any round; mr = mean rounds)

loop-s5: sums4 300/300/300/300/300/300/300/300/300 any 300 mr 6.55; sums6 250/275/289/299/298/297/297/297/297 any 299 mr 7.57; sums8 177/234/259/279/281/283/282/282/282 any 286 mr 8.45; grids5 75/207/300/300/300/300/300/300/300 any 300 mr 9.08; grids6 46/153/261/295/296/296/296/296/296 any 296 mr 10.61; grids7 15/93/157/226/239/239/241/240/241 any 245 mr 18.61; numbers4 0/1/1/2/1/1/1/1/1 any 2 mr 7.33; numbers5 1/0/0/0/0/0/0/0/0 any 2 mr 7.78; sums10 134/192/213/229/231/230/229/230/232 any 252 mr 9.24; sums12 87/130/167/179/179/179/178/178/179 any 206 mr 10.41.
loop-s6: sums4 300 x9 any 300 mr 7.07; sums6 254/273/290/297/297/297/297/297/297 any 298 mr 7.85; sums8 195/221/247/267/267/267/265/264/264 any 280 mr 8.70; grids5 106/204/297/300/300/300/300/300/300 any 300 mr 9.83; grids6 57/142/263/292/293/293/293/293/294 any 294 mr 12.36; grids7 16/85/152/222/216/215/214/214/213 any 227 mr 23.00; numbers4 4/2/4/4/4/5/5/5/5 any 7 mr 7.06; numbers5 0 x9 any 0 mr 7.54; sums10 167/195/212/228/226/227/227/225/226 any 255 mr 9.73; sums12 113/137/158/187/185/182/181/180/180 any 221 mr 10.63.
loop-s7: sums4 300 x9 any 300 mr 6.65; sums6 232/260/280/289/290/290/290/290/290 any 293 mr 7.16; sums8 151/175/213/232/238/235/235/234/234 any 254 mr 8.09; grids5 82/193/299/300/300/300/300/300/300 any 300 mr 9.77; grids6 45/134/239/285/283/283/283/283/283 any 291 mr 14.13; grids7 12/68/144/178/174/173/174/174/173 any 190 mr 28.12; numbers4 4/3/1/1/1/1/1/1/1 any 5 mr 7.70; numbers5 0/0/0/0/0/1/1/1/1 any 1 mr 8.29; sums10 127/142/170/169/172/173/171/171/171 any 195 mr 8.67; sums12 94/102/118/134/134/136/135/134/134 any 157 mr 8.93.
loop-s8: sums4 299/300/300/300/300/300/300/300/300 any 300 mr 6.58; sums6 247/262/288/296/294/293/293/293/293 any 298 mr 7.67; sums8 185/204/224/268/274/277/278/280/279 any 292 mr 9.18; grids5 119/224/300/300/300/300/300/300/300 any 300 mr 9.83; grids6 68/149/264/291/291/294/295/295/295 any 296 mr 12.18; grids7 13/86/163/216/215/215/215/216/217 any 224 mr 22.73; numbers4 0/0/0/0/0/0/1/1/1 any 1 mr 7.58; numbers5 0 x9 any 0 mr 8.21; sums10 149/168/186/214/232/234/232/233/234 any 264 mr 10.57; sums12 110/111/145/164/179/188/186/186/183 any 221 mr 11.93.

("x9" = same value at all 9 round settings.)

## Dev grids5 (dev rows; right/200) at 5k/10k/20k/40k/60k steps, per run

| run | 5k | 10k | 20k | 40k | 60k |
|---|---|---|---|---|---|
| loop-s5 | 186 | 200 | 200 | 200 | 200 |
| plain-s5 | 103 | 175 | 192 | 199 | 199 |
| loop-s6 | 58 | 195 | 200 | 200 | 200 |
| plain-s6 | 117 | 171 | 188 | 194 | 198 |
| loop-s7 | 84 | 189 | 200 | 200 | 200 |
| plain-s7 | 129 | 162 | 191 | 195 | 199 |
| loop-s8 | 42 | 182 | 200 | 200 | 200 |
| plain-s8 | 99 | 169 | 188 | 196 | 200 |
| plain-s1 | 131 | 168 | 192 | 197 | 199 |
| plain-s2 | 94 | 163 | 186 | 198 | 200 |
| plain-s3 | 116 | 168 | 182 | 191 | 197 |
| plain-s4 | 130 | 170 | 188 | 197 | 198 |

## steps_block_nograd per run (train_summary.json; 60000 steps each)

loop-s5 0, plain-s5 0, loop-s6 0, plain-s6 0, loop-s7 0, plain-s7 0, loop-s8 0, plain-s8 0, plain-s1 0, plain-s2 0, plain-s3 0, plain-s4 0 (12/12 zero).

## Minutes per run (train_summary.json "minutes")

loop-s5 78.5, plain-s5 75.2, loop-s6 82.1, plain-s6 79.1, loop-s7 75.0, plain-s7 71.2, loop-s8 78.0, plain-s8 76.1, plain-s1 61.2, plain-s2 58.6, plain-s3 50.8, plain-s4 50.4.

## Machine

GPU: NVIDIA GeForce RTX 5070 Ti (16303 MiB). torch 2.11.0+cu128, CUDA 12.8 (from `python -c "import torch;print(torch.__version__, torch.version.cuda)"`: `2.11.0+cu128 12.8`). Python venv C:/Users/benja/lis300/venv/Scripts/python.exe. nvidia-smi at start: 229 MiB used, 0% util, no compute processes (display-only processes). C: free 6321147904 bytes (~5.9 GB, above the 5 GB stop line).

## Report only: BensPC plain s1-4 vs rental plain s1-4 (origin/main), per test (mine minus rental)

plain-s1: sums4 +0, sums6 +10 (198-188), sums8 -4 (129-133), grids5 +0, grids6 +10 (240-230), grids7 +6 (142-136), numbers4 +0, numbers5 +0, sums10 +0 (93-93), sums12 +6 (71-65).
plain-s2: sums4 +0, sums6 -8 (201-209), sums8 -6 (110-116), grids5 -1 (299-300), grids6 -3 (245-248), grids7 -5 (144-149), numbers4 +1, numbers5 +1, sums10 -1 (59-60), sums12 -2 (42-44).
plain-s3: sums4 +0, sums6 -25 (152-177), sums8 -7 (58-65), grids5 -1 (296-297), grids6 -16 (221-237), grids7 +6 (136-130), numbers4 -1, numbers5 -1, sums10 +2 (29-27), sums12 +5 (12-7).
plain-s4: sums4 +0, sums6 +17 (234-217), sums8 +29 (175-146), grids5 -2 (298-300), grids6 +0 (236-236), grids7 +0 (142-142), numbers4 -2, numbers5 +1, sums10 +31 (143-112), sums12 +30 (119-89).
Machine difference (BensPC minus rental) is seed noise scale, mixed signs: biggest swings are plain-s4 sums10/12 (+31/+30) and plain-s3 sums6 (-25); practised tests agree within 2.

## Report only: 358i2 loop s1-4 (origin/builder-outbox) minus BensPC plain s1-4, per test

seed 1: sums4 +0, sums6 +101, sums8 +144, grids5 +1, grids6 +52, grids7 +44, numbers4 +2, numbers5 +1, sums10 +126, sums12 +93.
seed 2: sums4 +0, sums6 +98, sums8 +164, grids5 +1, grids6 +51, grids7 +97, numbers4 -1, numbers5 -1, sums10 +185, sums12 +160.
seed 3: sums4 +0, sums6 +146, sums8 +218, grids5 +4, grids6 +62, grids7 +37, numbers4 -1, numbers5 +1, sums10 +203, sums12 +181.
seed 4: sums4 +0, sums6 +63, sums8 +103, grids5 +2, grids6 +51, grids7 +35, numbers4 +1, numbers5 -2, sums10 +107, sums12 +79.
The 358i2 loop-vs-rental-plain gaps hold against same-machine BensPC plain: sums6 gaps +63 to +146 (mean +102.00), grids6 +51 to +62 (mean +54.00).

## Sealed checkpoint hashes (SEAL-run.sha256.txt; also on BensPC and Mac weight stores)

1ece3b96b2408fb3dc7a49d647baeb47d815c83321d9ee1c313ce9799b0b1841 W/loop-s5/final.pt (25764244 B)
5db6a4d15489f67ba96d9b63ce43408c7979214af86d2185caef133b7c492b30 W/plain-s5/final.pt (25573143 B)
2c84d41b4c3b22a5c238043d60456948f23b38a3afd2d56643e3e401dd5cfb36 W/loop-s6/final.pt
351c238fe746caad0e83dc18ab38e3bad5fbba8d7794b918799699f6146b49a9 W/plain-s6/final.pt
5238e843747df70e9be0e96e6160f842180ba3752ef6c7c9c54efa95574021b9 W/loop-s7/final.pt (25764244 B)
a30de8a242fa674854f9bec78b8eea14b3e3fca4ecd55e9c080025bb2df11999 W/plain-s7/final.pt
d733704ea2cb674feb334d6f20c4b3c4c8e0be31166d3edf0e7eba1a32a0a705 W/loop-s8/final.pt
99f519248bc7ac8b4ed07228f1f2a18b3d3b3f97ea81ea2efa9f9137a0ec0f95 W/plain-s8/final.pt
a280e634180bf7fd2ae5e43a728d098aa7b0b8e1e599ed1284b781c008ec19aa W/plain-s1/final.pt
cbd228360f6409ccdb886c36db6db6c57cebeca1967c6525646c975698d2966f W/plain-s2/final.pt
20a93f0b680df37e1653202b473ab06041ec26abde433b0417219924744483f9 W/plain-s3/final.pt
c631caed60fc87170d9607f64962ec065155cf5777f5c218b9a6f88795c5c079 W/plain-s4/final.pt
All 12 hashes are 64 hex characters; Mac copies at ~/premonition-models/rsn358i3/<R>/final.pt match byte for byte; BensPC copies at C:/Users/benja/premonition-models/rsn358i3/<R>/final.pt. No weights pushed.

## Every deviation

1. GPU-BUSY.txt pre-existed naming this job ("BUSY: queue job 100-claude-sleep-358i3pc ..."); per handoff/kit/benspc-task-header.txt the watcher owns that file, so I left it alone (did not create or delete it). No other job named it; no BUSY stop.
2. Detached launch method: PowerShell Start-Process children are killed when the Mac ssh session closes (both first runs died silently within a minute of disconnect; verified with a 90 s watched run that trained fine then died on disconnect, and a ping sleeper that died the same way). All 12 training runs were therefore launched via WMI Win32_Process.Create (Invoke-CimMethod), which survives disconnect; the training command line is byte-for-byte the specified one (defaults only, no extra flags). Wrapper cmd.exe PIDs recorded (loop-s5 3260, plain-s5 14696, loop-s6 17320, plain-s6 6484, loop-s7 18516, plain-s7 7684, loop-s8 21176, plain-s8 5204, plain-s1 7144, plain-s2 3096, plain-s3 5388, plain-s4 7556); nothing was ever stopped by PID.
3. Stdout went to W/<R>.log and stderr to a sibling W/<R>.err (cmd redirect `> log 2> err`); only the .log plus train_log.jsonl, train_summary.json, tests.json were copied back. BensPC W/ also holds the two empty first-attempt logs, t.log/t.err launch tests, and W/*-eval.out files (scratch only).
4. Parallelism followed the rule (2, then 3rd after 5+ min with 11.4 GB free, then 4th with 8.1 GB free; next started whenever one finished, in the specified order). Peak 4 at once.
5. 30-minute projection (at ~20:50Z, loop-s5 30000 steps/36.3 min): all graded runs finishing ~21:25-21:50, everything inside the 10 h cap; nothing dropped, no TOO-SLOW, run is conclusive. Actual: first launch ~20:13Z, last train done 00:41Z (~4.5 h training); 12 seal+eval steps and copy-back followed the same night, total well inside the 10 h cap.
6. C: free was 6.3 GB (above the 5 GB stop line; reported as tight but go).
7. SEAL-code check used C:/Program Files/Git/usr/bin/sha256sum.exe (cmd has no sha256sum); 19/19 OK before any training.
8. Selftest outputs carry detail suffixes ("selftest ok: ..." and "check-mask ok: ..."); all three printed their ok lines.
9. 358i2 loop s1-4 reference came from origin/builder-outbox (not yet on main), as the task allowed.
10. Code never edited; on any breakage I would have stopped (nothing broke). Each eval ran exactly once per checkpoint file (12 evals, 12 tests.json). TEST-ONLY items never opened; only counts were read.
