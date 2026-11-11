# Passive measurements of the live PC job 8aG2C3S (arm PTS), 10-13 9:54 to 10:42 PM ET

Taken by the Mac helper over ssh. Nothing killed, paused or installed into the job's Python. Only new files in `C:\Users\benja\custom-io\work\speedup-prof\`. Labels: shown = measured or read from a log; suggested = reasoning.

## Job
- 8aG2C3S-3M-s400, arm PTS (plain_tf_steps_g, all_steps, d 256, hidden 1066, 4 layers, 4 heads, eg_embed), 4,023,976 trained params, 1,343,273 rows, pool `p10-rung30-s400-a64-L`, caps PTS.
- `--steps 24000 --batch 256 --accum 16 --bf16 --lr 0.001 --log-every 500 --final-eval --max-ans 8`. Started 4:14:15 PM ET (pid 31652).
- Machine: RTX 5070 Ti, Ryzen 5 7600X (12 logical cores), Windows, WDDM.

## Speed (shown, from PTS\stdout.txt)
| step | elapsed s | s per 500 steps |
|---|---|---|
| 17500 | 18713.4 | |
| 18000 | 19275.0 | 561.6 |
| 18500 | 19828.5 | 553.5 |
| 19000 | 20398.8 | 570.3 |
| 19500 | 20983.5 | 584.7 |
| 20000 | 21569.9 | 586.4 |
| 20500 | 22102.7 | 532.8 |
| 21000 | 22620.7 | 518.0 |
| 21500 | 23140.8 | 520.1 (10:40 PM ET) |

Whole run so far: 21,500 steps in 6.43 h = 0.929 updates/s, so one 24,000-update run of this arm is about 7.2 h. (The earlier "2.4 h" came from the G-PT arm without the Gemma front.) Training should end about 11:25 PM ET; then the final eval, then the waiter's 5 quiet minutes, then G2f.

## GPU and CPU (shown; 120 one-second samples, 9:54:53 to 9:56:53 PM ET)
- GPU utilisation mean 75.6 % (min 34, max 96); clocks.sm 2886 MHz; power 148 W (116 to 172); temperature 47 C; memory used about 12.1 GB.
- Trainer process: 0.92 of one core busy; 8 threads; working set about 2 GB; private 15 GB.
- Machine CPU about 36 % (4.3 logical cores). Ben's Minecraft (Lunar Client javaw) uses 1.15 cores and probably some GPU; llama-server is resident but idle (holds at most about 1.2 GB GPU).

## py-spy (shown; 120 s, 25 Hz, 2973 samples, 0 errors, no visible slowdown)
Python-thread samples only: waiting on the GPU queue is charged to the Python line that blocks, so host cost and GPU waiting are not separated.
- 75.5 % of samples inside `eg.encode/_compute` (frozen EmbeddingGemma 2 forward), reached through `plain_tf_steps.loss -> plain_lm._set_front` (76.2 %).
- Self time: Gemma `forward` 20.6 %, Gemma `_norm` (RMS norm) 19.5 %, Linear 11.7 %, `plain_tf_steps._targets` 6.2 %, `eg._compute` 4.8 %, sdpa mask creation 3.7 %, sdpa attention 3.7 %, rotary 2.8 + 2.6 %, tokenizer 2.1 %.
- Backward 0.9 %, data loading and collate under 1 %.
- Code check (shown, `custom_io/models/plain_lm.py:76-84` at 74d6e92c75): `_set_front` calls `eg().encode(...)` on every micro-batch, so Gemma runs 16 times per update on 16 rows each, and `encode` memoises only its last call (`models/eg.py`).

## Length statistics (shown; `len_pad_sim.py`, outputs `len-L.json`, `len-a64.json` on the PC)
-L pool: prompt chars mean 176, p50 117, p90 278, p99 699, max 2000; web prompts p99 1297. a64 pool: max 280.
Padding at accum 16 (linear cost): padding to the widest row of the whole update costs 6.09 times sorted micro-batches and 8.48 times no padding on the -L pool; on the a64 pool 1.60 and 1.67.
Caveat (shown in `plain_tf_steps.py:loss`): the transformer width W is taken from each micro-batch's own row lengths, so the PTS thinker is not padded to the update-wide width; only the Gemma-state expansion `H [B,T,768]` uses the update-wide T. Where the padding cost lands for other arms (B3G2) is for the profile to say.

## Open
- Free disk on C: fell 153.8 -> 148.1 GB between 10:22 and 10:32 PM ET, then held at 148.2 GB at 10:42 PM. Cause not found.
- `REQUESTS_CA_BUNDLE` on the PC points to a missing file (breaks pip); not changed.
