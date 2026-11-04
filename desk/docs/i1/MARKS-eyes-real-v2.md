# MARKS: Glim can see, real-model check v2 (track I1, written 2026-11-04 14:20 before the run; never edited after it starts)

Why v2: v1 (MARKS-eyes-real-v1.md) was stopped by me after 28 min with no result: 1,000 full forwards of ~300 tokens take ~2-3 s each
on this M1 Pro under the other agents' load (measured 2.0-3.7 s), so it could not finish inside the 30-minute job limit. No v1 number
was seen. ONE change: n = 20 instead of 50, and the media prompt is run once per image with its KV cache reused for the 10 captions
(trimmed back after each); everything else, including the pass marks, is unchanged.

| id | test | pass mark |
|---|---|---|
| R1 | retrieval top-1 of 10 (seed 0 candidates among the first 20 held-out thumbnails), caption log-likelihood given the image | >= 40 % |
| R1-control | the same with each image's features swapped for another image's (shuffled, seed 7) | <= 25 % (chance 10 %) |
| R2 | text-only chat request, greedy 40 tokens, through glim_mlx_server.py with --eyes on vs --eyes off | identical text |
| R3 | 8 greedy captions (48 tokens) through the real HTTP server (glim_mlx_server.py --eyes on, port 18099), image_features parts | >= 7 of 8 non-empty, no 4-gram repeated 3+ times |
| R4 | eyes speed on this M1 Pro, 1280x800 frame, f16 (already measured before this file: 22-24 ms, peak 345 MB) | median <= 100 ms/frame, peak MLX memory <= 600 MB |

What would prove it wrong: R1 within 10 points of its control; R2 differs; R3 degenerate. Label: REAL, n = 20 (a wiring check;
n = 20 can only suggest, not show, vision quality on q8).
