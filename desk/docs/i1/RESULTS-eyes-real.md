# RESULTS: Glim can see, REAL checks (track I1, 2026-11-04, M1 Pro, Nanbeige4.2-3B 8-bit MLX)

Marks: MARKS-eyes-real-v2.md (v1 stopped with no result: too slow for the 30-min limit; one change, see v2).

| id | mark | result | verdict |
|---|---|---|---|
| R1 | retrieval top-1 of 10 >= 40 % (n = 20) | **60 %** (12/20) | PASS |
| R1-control | shuffled features <= 25 % | 20 % (4/20), chance 10 % | PASS |
| R2 | text-only answer identical, eyes on vs off (real HTTP server) | identical | PASS |
| R3 | >= 7/8 non-degenerate captions through the real HTTP server | 8/8, all on topic (two women at a bar, a polo shirt, a book cover, a thumb-brace package...) | PASS |
| R4 | eyes <= 100 ms/frame, <= 600 MB | 22-24 ms/frame (f16), peak 345 MB MLX, 233 MB RSS | PASS |

Also: the KV-cache scoring equals a full forward (-86.03 vs -85.97 nats on one caption); peak 5.1 GB during R1.
Encoder port: MLX f32 vs transformers SiglipVisionModel max |diff| 3e-4 (2 test images); f16 cos 0.99994.

What this shows (real): the image reaches the q8 model through the server and steers it (60 % vs 20 % shuffled), and text-only use is
unchanged. What it does not show: n = 20 thumbnails (160 px) is small and low-resolution, so it suggests rather than shows that q8 keeps
the projector's bf16 quality (V1 67.6 % on n = 500); screen frames (text-heavy UI) are not like ReCap photos and are untested; no sense
night has run on the real model.
