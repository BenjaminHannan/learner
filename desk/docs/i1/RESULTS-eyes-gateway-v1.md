# RESULTS: Glim's eyes through the gateway, v1. REAL (track I1b, 2026-11-04, M1 Pro, Nanbeige4.2-3B 8-bit MLX)

Marks: MARKS-eyes-gateway-v1.md (committed e6f5af65c before the run). Raw: eyes-gateway-v1/A-nanbeige.json, B-glim.json, run.log.
**Verdict: PASS.** config.sh is left on `ASSISTANT_ENGINE="glim"`, running, gateway up on :8090.

| id | mark | result (run B, glim engine) | verdict |
|---|---|---|---|
| G1 | 3 text replies identical to the old engine's + thinking request works | 3/3 identical (temperature 0); thinking: 200, answer + 1780 chars of reasoning | PASS |
| G2 | >= 2 visible things named in >= 4 of 5 pictures | **5/5** (weather 4 things, shop 4, dog 2, map 3, chart 3) | PASS |
| G3 | shuffled-features control <= 1 of 5 | **0/5** (each reply describes the picture whose features were sent) | PASS |
| side look | old engine, same picture requests | 0/5: "I cannot directly view or analyze images..." (gateway placeholder) | as expected |

Replies (first words): "a digital weather forecast for a sunny day with a temperature of 55°F ... a stylized sun"; "a digital marketplace ...
'Apple' and 'Banana' ... a red apple with a green leaf, a price tag"; "a cartoon-style illustration of a dog with a white face"; "a digital
map interface ... navigation"; "a bar chart titled 'Monthly Sales' ... January to June 2019".
Wrong details: 55°F (picture says 75°F), "January to June 2019" (Jan-May, no year), dog colours. The eyes give the gist and big words, not
exact small text or numbers.

## Speed and memory (both runs under heavy load from other agents: 1-min load 16-28)
| | old engine (nanbeige) | glim engine |
|---|---|---|
| start to ready | 8 s | 11 s |
| text replies (3 prompts) | 23.3 / 2.1 / 7.3 s | 22.9 / 2.1 / 8.0 s |
| thinking reply | 65 s | 69 s |
| picture reply (120 tokens) | n/a (cannot see) | 21-22 s each |
| eyes (SigLIP2, client side) | n/a | 75-90 ms/frame warm (245 ms first) |
| big server idle footprint / RSS | 4.69 GB / 3.58 GB | 5.13 GB / 5.16 GB |
| big server peak footprint / RSS | 9.94 GB / 9.57 GB | 10.24 GB / 9.57 GB |

Text speed is the same within noise. The glim engine costs ~0.45 GB more at idle (projector weights; it is 768->3072->3072 in
f16). Latencies are inflated by the load; compare the two columns, not absolute numbers.

## The engine switch (one line)
- `~/learner-ops/assistant/config.sh`: `ASSISTANT_ENGINE="glim"` (eyes) or `ASSISTANT_ENGINE="nanbeige"` (old, no eyes).
- Then `~/learner-ops/assistant/stop.sh && ~/learner-ops/assistant/serve.sh --yes` (the gateway must restart too: serve.sh sets
  ASSISTANT_PASS_FEATURES=1 only for glim).
- "glim" runs `assistant/glim/glim_mlx_server.py` (a stable copy of desk/tools at 6e07b4ee6, hashes in assistant/glim/SHA256.txt) with
  `--settings-file <userData>/settings.json --eyes on --keep-in-memory off`, the same model, port, prefill, cache and max-tokens
  arguments as "nanbeige". Projector: `userData/sense-sleep/vision_projector.safetensors` if sense sleep kept one, else the published v1.
  The live wrapper dory/plain_mlx_lm_big.py is untouched.
- Backups: gateway.py / serve.sh / config.sh / stop.sh `.bak-pre-eyes-1793823794` in ~/learner-ops/assistant.

## What differs for the app
- Same model ids (`lfm3`, `lfm3-fast`, `lfm3-auto`), same thinking rule (only `-fast`/`-auto` turn it off), same gateway wrapper
  (sleepmlx.mac_gateway), same 2048 max. Text answers identical at temperature 0.
- The old "nanbeige" engine never used Dory loops or a sleep adapter (stock mlx_lm), so neither does "glim".
- New: an `image_features` part now reaches the model and is described. With the old engine it becomes "[image_features omitted ...]".
- A request with image_features is served alone (mlx_lm's rule for image requests), so it does not batch with a parallel chat.
- "Keep brain in memory" is forced OFF (as before); the app's keepBrainInMemory setting is not read by this engine.
- The diary stores a sha256 placeholder for the features part, never the features.
- If the eyes fail to start (bad projector file) the server logs `[glim-eyes] could not start the eyes` and serves text only.

## Gateway change (tested)
`strip_non_text()` keeps `image_features` parts when ASSISTANT_PASS_FEATURES=1; nothing else changed (diff = 7 lines). Tests:
`~/learner-ops/assistant/tests/test_eyes_passthrough.py` (9 pass): features survive prepare() (plain and as served through
mac_gateway), dropped as before when the flag is off, other non-text parts still stripped, text-only prepare() output byte-identical to
the pre-change gateway (flag on and off), image_url still captioned by the vision route, the diary never holds the features. Full gateway
suite: 83 tests, 1 failure (test_prefix_saved_warmed_and_rewarmed), which fails the same way on the unchanged gateway.

## Seat set
Built: `userData/sense-sleep/seat/vision_seat.{safetensors,json}` (50 held-out ReCap thumbnails, 64 x 768 f16, eye
siglip2-base-patch16-256/pool2x2/v1, 10 candidates each, seed 0). SLEEPMLX_SENSE_SLEEP stays unset (off).

## Claims
- Shown (real, n = 5): pictures rendered as screen-like pages reach the q8 model through the real gateway and the model describes the
  right picture (5/5 vs 0/5 shuffled); text chat is unchanged.
- Suggested: the eyes give the gist (objects, page type, big words) but not exact numbers or small text.
- Untested: real busy screens; the app's own always-on system prompt and question; the in-app path end to end; a sense-sleep night.
