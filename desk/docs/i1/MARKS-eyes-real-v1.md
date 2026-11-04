# MARKS: Glim can see, real-model check v1 (track I1, written 2026-11-04 before the run; never edited after it starts)

Model: the day-time Nanbeige4.2-3B **8-bit MLX** (~/learner-ops/models/nanbeige42-3b-mlx-8bit). The projector was trained against
**bf16** Nanbeige on the PC; q8 use is untested (projectors README). Encoder: the MLX SigLIP2 port in desk/tools/glim_eyes.py (f16).
Images: the 50 held-out ReCap shard-25 thumbnails saved in premonition-projectors/results/vision_captions.html (160 px, JPEG,
so worse than the 256 px originals), with their reference captions (first 300 characters).

| id | test | pass mark |
|---|---|---|
| R1 | retrieval top-1 of 10 (true caption vs 9 others, seed 0), caption log-likelihood given the image, n = 50 | >= 40 % |
| R1-control | the same with each image's features swapped for another image's (shuffled) | <= 25 % (chance 10 %) |
| R2 | text-only request: greedy 40 tokens, server with eyes ON vs the stock path in the same process | identical tokens |
| R3 | 8 greedy captions (48 tokens) through the real HTTP server (glim_mlx_server.py --eyes on, port 18099) | >= 7 of 8 non-empty, no 4-gram repeated 3+ times |
| R4 | eyes speed on this M1 Pro, 1280x800 frame, f16 | median <= 100 ms/frame, peak MLX memory <= 600 MB |

What would prove it wrong: R1 within 10 points of the shuffled control (the image does not reach the model); R2 differs (the text path
changed); R3 degenerate output (splice or scale wrong on q8).
Seeds: retrieval candidates seed 0; one run (this is a wiring check, not a claim about vision quality). Label: REAL, n = 50.
