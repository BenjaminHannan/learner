# MARKS: Glim's eyes through the gateway, v1 (track I1b, 2026-11-04). REAL check, M1 Pro, Nanbeige4.2-3B 8-bit MLX

Written and committed before the run. Not edited after the run starts.

## What runs
- Gateway on :8090 (`serve.sh --yes`, as the app starts it: `python -m sleepmlx.mac_gateway --gateway-file gateway.py`).
- Run A, old engine: `ASSISTANT_ENGINE="nanbeige"` (dory/plain_mlx_lm_big.py, stock mlx_lm). The gateway does not pass features.
- Run B, new engine: `ASSISTANT_ENGINE="glim"` (assistant/glim/glim_mlx_server.py `--eyes on`, published v1 projector unless sense
  sleep kept one; ASSISTANT_PASS_FEATURES=1).
- Client: `eyes-gateway-v1/check.py` (same for both runs). Each run goes through `/tmp/aon/realmodel-lock.sh`, memory pressure 1 first,
  < 30 min each.
- Pictures: 5 screen-like pages rendered by headless Chrome from `eyes-gateway-v1/pages/*.html` at 1280x800 (no screenshot of Ben's
  screen). Features: glim_eyes.py (SigLIP2, 2x2 pool, 64 x 768), sent as an `image_features` part before the text
  "\nDescribe this image.", model `lfm3-fast` (thinking off), temperature 0, max 120 tokens.

## Pass marks (run B)
| id | mark |
|---|---|
| G1 text-only works | 3 text prompts (`lfm3-fast`, temperature 0, max 40) give non-empty replies identical to run A's, AND a thinking request (`lfm3`, max 400) returns 200 with a non-empty answer or reasoning |
| G2 pictures | the reply names >= 2 visible things of its picture in >= 4 of 5 pictures (things = the word lists in check.py `THINGS`, graded automatically, disjoint across pictures) |
| G3 control | shuffled features (picture i's question with picture (i+2) mod 5's features, graded against picture i's things) pass <= 1 of 5 |

Verdict: PASS only if G1, G2 and G3 all pass. Then config.sh stays on "glim". Otherwise config.sh goes back to "nanbeige".

## Reported, not marked
- Speed: load time to ready, text latency (mean of the 3), picture request latency, eyes ms/frame.
- Memory: big-server RSS and `footprint` (idle and peak) for both engines.
- Run A's picture replies (the old engine gets a placeholder, so it should not describe the pictures; a side look, not a mark).

## What would prove it wrong
- G2 < 4/5: the eyes do not survive the gateway, or screen-like pictures are outside what the projector learned (ReCap photos).
- G3 > 1/5: the replies are generic (any screen gets the same words), so G2 would not show seeing.
- G1 fails: the glim engine or the gateway change altered text chat.

## Limits (known before the run)
- n = 5, one prompt, temperature 0: a smoke check of the path, not a quality measure.
- The pictures are simple, high-contrast pages with big emoji/shapes; real screens are busier. The app's own system prompt and question
  are not used (I1 limit 5).
