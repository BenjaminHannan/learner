# E1: intake + speed (2026-11-04)

Three settings, all OFF in code: `keepBrainInMemory`, `moteBatch`, `senseChangeOnly`. The prompt re-order is always on, because it keeps the meaning the same.
The measurements and marks are in ~/learner-ops/premonition-e1 (MARKS-E1.md, results/). They come from a tiny model or a simulation, not from real Glim.

## What stock mlx_lm 0.32.2 already does (read from the installed code)
- At start it sets the wired limit to `max_recommended_working_set_size` (30 GB on the M1 Pro), and it puts it back after every generation. So the live server already wires what MLX allocates.
- It keeps an LRU prompt cache and reuses the longest shared prefix.
- It batches requests that arrive together. This needs a cache with `merge` (Nanbeige's KVCache has it), no `seed`, and no `--kv-bits`. `--draft-model` turns batching off.
- A non-streamed request keeps running after the client hangs up. A streamed one is dropped at its next token.

## Pieces
- `tools/glim_mlx_server.py`: a drop-in for `~/learner-ops/assistant/dory/plain_mlx_lm_big.py`, which was not touched.
  - Off: stock behaviour.
  - On: wired limit = weights + KV buffer + 512 MB, held fixed. The pool is fixed and pre-touched, `clear_cache` does nothing, and the prompt cache is capped at the buffer size.
  - Nanbeige 8-bit plus a 2 GB buffer is about 6.6 GB that stays wired.
  - Tests: `python -m pytest -q tools/test_glim_mlx_server.py`.
- `src/alwayson.js` `buildMessages`: the same lines in a new order, stable first and changing last. `buildMessagesV1` keeps the old order.
- `src/motebatch.js` + `MotePool.canBatch`: with `moteBatch` on, a Mote's K tries go out together, streamed, with one shared abort. If Ben types, `stopAll` aborts all of them.
- `src/senses.js` `sampleChangeOnly`: with `senseChangeOnly` on, the cheap windows/accessibility look runs every 5 s. Screen OCR runs only when that look changed, or when 60 s have passed (rich accessibility text) or 20 s (poor text). OCR stores only the lines that changed. With the windows sense off, the screen stays on 20 s.

## Brain in memory: what the tiny-model tests found (premonition-e1/results/M1-result.md)
- MLX's wired limit does not keep an idle server in RAM on this Mac. ON, OFF (the live behaviour) and no-limit were all
  compressed or swapped within about a minute of idle. That is the "slow first reply after a quiet spell".
- `--keep-touch-s 10` (GPU read of one value per page while idle) kept the model resident in 29/35 samples, against 0/140 without
  it. Post-idle first-token time was about half. This is NOT a pass: it was still swept now and then, and first-token time stayed
  above 2× warm.
- The CPU touch (`--keep-touch-mode cpu`) did worse. Don't use it.
- Suggested launch if the lead tries it: `--keep-in-memory on --keep-touch-s 10`, or the settings toggle plus `--keep-touch-s 10`.

## What the lead must check on the real app
1. **Brain in memory.**
   - In `serve.sh`, change the nanbeige `launch big` line from `$DIR/dory/plain_mlx_lm_big.py` to `~/learner-ops/desk-always-on/desk/tools/glim_mlx_server.py --settings-file "$HOME/Library/Application Support/Premonition/settings.json"`. Keep all other args.
   - With the setting off, check the log line `[glim-brain] keep in memory OFF` and that chat works as before.
   - Turn on "Keep Glim's brain in memory", add `--keep-touch-s 10`, and restart the server. The log should say a wired limit of about 6.6 GB, not capped, plus `idle touch every 10.0s (gpu)`.
   - Check the GPU region: `vmmap -summary <pid> | grep "IOAccelerator (graphics)"` SWAPPED should stay near 0 after 10 min idle, and DIRTY should stay near full. Without the touch, expect it to be swapped.
   - After 30 min idle with Ben's normal apps open, time the first reply against a warm one.
   - Watch memory pressure for an hour (`sysctl kern.memorystatus_vm_pressure_level` should stay at 1).
2. **Batching.**
   - Turn on "Think in parallel" and let Glim get bored.
   - The server log should show the 4 tries arriving together, and the "thought" diary lines should arrive about 2× sooner.
   - Type into chat during a batch. The reply must start as fast as usual, and the server log must show the batch requests cut short. This also confirms the 8090 gateway closes the upstream stream when the client hangs up; that has not been checked.
3. **Change-only intake.**
   - With Open windows and Screen on, turn on "Look more often, read only changes".
   - Over 30 min, compare the deskhelper CPU (Activity Monitor, or `ps -o time` of the app's helper children) with 30 min with the setting off.
   - The simulation only passes if OCR costs at least about 9× one windows+look pair. Check that ratio on the real Mac.
   - Check the inbox: window switches should appear within about 5 s, and screen entries should start with "Changed on screen:".
4. **Prefix reuse.** In the gateway log, look at `cached_tokens` for consecutive always-on ticks. Expect roughly 45% of each prompt to be cached; the tiny-model estimate was 0.47.
