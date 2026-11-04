# Glim can see + sense sleep live (track I1, 2026-11-04): lead note

Everything ships OFF: `glimCanSee`, `keepSenseEvidence` (Desk settings) and `SLEEPMLX_SENSE_SLEEP` (sleep worker env).

## The pieces
| Piece | Where | Tests |
|---|---|---|
| Eyes: MLX port of the SigLIP2-base-patch16-256 vision tower, training preprocessing (BICUBIC 256, mean = std = 0.5), 2x2 pool -> 64 x 768, a JSON-lines worker | `desk/tools/glim_eyes.py`; weights `~/learner-ops/models/siglip2-base-patch16-256-vision/` (vision tensors only, bf16, 186 MB; range-read from the HF file, 372 MB downloaded) | `desk/tools/test_glim_eyes.py` |
| Model server: `image_features` content parts -> projector -> 64 rows spliced where the part was (text before/after tokenized separately, as in training); Nanbeige gets an `input_embeddings` argument; text-only requests take the stock path | `desk/tools/glim_mlx_server.py` (`--eyes on|off`, else settings.json `glimCanSee`; `--eyes-projector`, else `userData/sense-sleep/vision_projector.safetensors` if sense sleep made one, else the published v1 file) | same file (tiny real Nanbeige: ids path == embeddings path, with and without KV cache; end-to-end through stock `generate_step`) |
| Desk day: screen read -> (not private) screenshot 512 px -> eyes worker -> FeatureStore record (screen words = text anchor, front app = title) + the latest frame for the always-on loop's next ask (once, < 2 min old) + optional raw evidence | `desk/src/eyes.js`, hook `onScreen` in `src/senses.js`, wiring in `main.js` (`aoEyes`, `aoAskSeeing`, nightly job) | `desk/test/eyes.test.js` (11) |
| Raw evidence store: JPEGs in `userData/sense-evidence/<day>/`, Mac only, 3 days, 2 GB (oldest first), never when the screen/windows look private (incl. Private Browsing / Incognito / InPrivate / password managers) | `EvidenceStore` in `src/eyes.js` | yes |
| Night (Desk): one eye practice manifest per day (`sense-sleep/practice-<day>.json`), ears emptied, feature days > 3 days pruned unless a kept night pins them, evidence pruned | `Eyes.nightly()` | yes |
| Night (sleep app): T4 `sense_projector.py` + T4b `sense_encoder_lora.py` applied; `sense_night.py` trains the eye projector on the q8 model, seat-set seatbelt, exact byte rollback + quarantine, benFirst checked between steps; runs after a finished brain night or on a "no new day" night; any error skips it | `sleepmlx/sense_night.py`, `worker._sense_step` | `sleepmlx/tests/test_sense_night.py` (9; tiny 8-bit Nanbeige: gradients reach the projector through quantized layers, loss falls, poisoned night restored byte for byte, Ben-back mid-training rolled back) |

Not wired on purpose: the encoder LoRA (T4b; eye encoder is fine), the ears (sound projector failed A1), the 2-of-3 rule (T4: not proven).

## Lead must decide
1. **Seat set.** The projector night refuses to train without one (`userData/sense-sleep/seat/vision_seat.*`). Interim option (on this Mac,
   2 min): `python desk/tools/build_vision_seat.py --userdata "$HOME/Library/Application Support/Premonition" --from-html ~/learner-ops/premonition-projectors/results/vision_captions.html`
   (50 held-out thumbnails, 160 px). Better: 150+ full-size ReCap shard-25 images, built on the PC (`--from-jsonl`). With 50 items one
   item = 2 points, so the "drop > 2" seatbelt rolls back at 2 items lost: strict.
2. **q8 instead of bf16.** There is no disk room for the 8 GB bf16 copy, so the night trains and checks on the q8 day-time model (the one
   that matters by day). This is tested only on a tiny model. bf16 is not checked at all.
3. **Night length.** Measured on this M1 Pro under load: a ~300-token forward of q8 Nanbeige takes 2-4 s. The seat check runs each
   image's prompt once and reuses its KV cache for the 10 captions (`LM.score_candidates`, tested equal to full forwards). Estimate
   (not measured on the real night): 50 seat items ~ 5-10 min per check, twice a night, plus 40 steps x 4 items of training
   (~10-20 min): ~30-40 min per eye night.
4. **The gateway.** The always-on loop's asks go to `gatewayUrl`. The image part reaches the model only if the Mac gateway passes
   content lists through unchanged (the Desk's built-in gateway only writes text to the diary; the Premonition gateway on Ben's Mac is
   not in this repo). Check step 4 below.
5. **System prompt.** The projector was trained with Nanbeige's default system prompt and "Describe this image."; the loop sends its own
   system prompt and question. Untested.

## Exact steps for the real-app check
1. `cd ~/learner-ops/desk-always-on/desk && ~/learner-ops/nb2-venv/bin/python -m pytest -q tools/test_glim_eyes.py tools/test_glim_mlx_server.py`
2. Start the server the app uses through E1's wrapper with eyes: add `--eyes on` (or set `"glimCanSee": true` in settings.json and pass
   `--settings-file`). Its log must say `[glim-eyes] Glim can see ON: projector ...`.
3. `python /tmp/i1scratch/real3_client.py on` style request against the real port: a text-only request must answer as before; an
   `image_features` request must describe the picture.
4. In the app: Settings > Senses > "Glim can see" on, Screen sense on (and "Look more often" on if wanted). Watch the log for
   `[eyes]` lines; `userData/sense-sleep/features-<today>.jsonl` gains a line per screen read; open a Safari Private window: no line,
   no picture. Check the gateway log that the always-on request kept its `image_features` part.
5. "Keep screenshots for 3 days" on: `userData/sense-evidence/<today>/` fills; it must stay under 2 GB and lose days older than 3.
6. Night: Desk writes `sense-sleep/practice-<day>.json` (eye entries only). Sleep worker with `SLEEPMLX_SENSE_SLEEP=1`: its chunk output
   gains `sense_sleep` with `nights: [{kept, reason, before, after}]` or a `skipped` reason; `nights.jsonl` gets a line.
