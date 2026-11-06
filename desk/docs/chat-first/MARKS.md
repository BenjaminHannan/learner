# CHAT-FIRST: Ben's chat never waits behind Glim's background thinking (2026-11-05). Pass marks, fixed before any code.

Problem (ONE-GLIM, shown): with glimCanSee on, every always-on tick carries a ~1 MB screen clip (5-8k tokens) that the brain serves
alone. A chat arriving meanwhile queues behind it: first token 40-70 s, some chats time out at 180 s.

Checked in code before building (shown):
- The gateway closes its upstream connection when the Desk aborts (`finally: conn.close()` after relay_stream / relay_plain).
- A batched streamed request stops at its next step once the client is gone (mlx_lm batch loop checks `ctx._should_stop`).
- A request served alone (clip/picture requests, and prompts > solo-tokens 4096) goes through mlx_lm `_serve_single`. That path
  checks `ctx._should_stop` only in the token loop, after the whole prompt is read. **So streaming alone does not free the brain
  during a clip's prefill.** Part (b) therefore also needs a guard-side stop between prefill chunks (see change B2).
- A non-streamed request (today's aoAsk: ticks, checks, quiz, non-batch Motes) runs to the end whatever the Desk does.

## Changes (one at a time, each with its own unit tests; one shared brain restart for B2 + A2)

- **A1 (Desk) chat hold.** No tick, Mote, check, quiz or other always-on request *starts* while a chat run is in flight or within
  120 s after Ben's last chat message. One gate inside the always-on ask itself (so no caller can skip it), independent of the
  `benFirst` setting. Messages: chat start sets `lastChatAt`.
- **A2 (gateway) re-warm hold.** The gateway's idle prefix re-warm does not start within 120 s after the last real chat request
  (non-test) began; it waits and retries.
- **B1 (Desk) stream every always-on ask.** aoAsk becomes streamed (same body otherwise), so the existing cancels (chat start, typing)
  close the connection and the server sees it.
- **B2 (guard) stop during a lone prefill.** While a request served alone is reading its prompt, the guard's progress hook checks the
  request's stop flag and ends the prefill at the next 512-token chunk. Nothing of the stopped prompt is saved to the cache.
- **C (Desk) clips only on a meaningful change.** An always-on tick carries a clip only when the newest frame differs meaningfully
  from the last frame Glim was *sent* (feature cosine < 0.98) AND ≥ 180 s since the last clip; a single picture only on the same
  meaningful change; else no picture at all (the text senses still go). A chat that asks about the screen keeps its own path.

## Pass marks

**P1 chat first word (real brain, lock queue, Ben idle gate).** Script `cf_test.py`. 5 pairs; each pair uses a real chat request
(final6k replay, a fresh nonce per send so neither half is a cache hit beyond the shared system+tools prefix):
- clear: the chat alone, queue empty → TTFT_clear;
- contended: a streamed tick carrying an 8-frame clip (the app's clip shape, 512 feature rows + a real tick prompt) is started;
  2 s later it is aborted exactly as the app does on chat start, and the chat is sent → TTFT_cont.
- **Pass: TTFT_cont ≤ TTFT_clear + 2 s in all 5 pairs.** Fail if any pair is > +2 s.
- Also logged: the server line showing where the aborted clip stopped (must stop ≤ 1 chunk after the abort).

**P2 no chat times out.** In the P1 run and in the live window after install (until this report is written, ≥ 1 h of real use if
Ben chats): 0 chat requests (gateway `system=3000`) without a first token within 180 s, and 0 Desk "timed out" chat errors.

**P3 the always-on tick still works when Ben is quiet.** After install, glimCanSee on, m1see.sh run (screen unlocked) + a 20-min
idle window: ticks complete (gateway `system=1110` requests finish 200, Desk log shows a decision) at ≥ 1 per 5 min while Ben has
been away > 120 s; ≥ 1 tick carries a clip while a video plays (m1see.sh); and m1see.sh's two sight questions still answer (its
see-*.json non-empty). Fail if ticks stop when Ben is quiet, or no tick ever carries a clip on a moving screen.

**Unit marks (desk tests, before any build):**
- U1: with a chat in flight, or < 120 s after the last chat message, the always-on ask refuses without a network call; at 121 s it asks.
- U2: aoAsk sends `stream: true` and returns the joined text; aborting it aborts the fetch.
- U3: seePart for ticks: still screen → null after the first send; small change (cos ≥ 0.98) → null; big change → frame/clip; a
  second clip within 180 s → at most a single picture.
- U4 (guard, Python): a lone request whose stop flag is set during prefill raises out of the prefill within one chunk, and the cache
  insert is skipped.
- Full desk suite: no failures beyond the known list.

**What proves it wrong:** any P1 pair > +2 s; any chat > 180 s; or ticks no longer run / never see a moving screen.

Rules: real-brain tests only via `realmodel-lock.sh`; build/install only with Ben idle ≥ 5 min; B2 + A2 go live in ONE brain restart,
after MEM-GUARD's live run releases the lock, coordinated with MEM-GUARD (same guard file); exact-PID kills only.
