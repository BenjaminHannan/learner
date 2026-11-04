# Always-on v2: decisions made overnight (2026-11-04, Ben asleep)

Spec: always-on-v2-design.md. Each line: what was decided and why.

## Phase 0
- **Merge main**: nothing to merge. GitHub `main` (41a777b, #305, fetched 23:55) is already an ancestor of `always-on`. The local
  `main` ref (e7439b331, #258, Oct 28) is a stale shallow graft with no shared history, and its content is older than what
  always-on already has (#269, #271). Merging it would have meant `--allow-unrelated-histories` over an older tree, so it was skipped.
- **Baseline suite after "merge"**: 669 tests, 2 failures (open_app refuses browsers; 8192-token prompt budget). The v1 brief's
  third known failure (first-reply thinking cap) passes now.
- **Model**: chat on Ben's Mac sends `settings.modelFast` (= `qwen36-fast`) to the Premonition gateway on :8090, whose big
  upstream is Nanbeige4.2-3B (`~/learner-ops/assistant/config.sh`: `ASSISTANT_ENGINE="nanbeige"`, stock mlx_lm, no Dory loops).
  v1's `lfm3-fast` is unknown to that gateway and was routed to Nanbeige *with thinking on*. The loop now uses
  `chatModel(settings)` = chat's Fast id + chat's gateway URL. Motes already used chat's settings (only mode/compaction change).

## Phase 1 (notch voice + status)
- **Typing guard**: "typing" = Desk's composer typed in the last 15 s OR any Mac input in the last 2 s (system idle time).
  A message waits for a 4 s pause; if Ben keeps going for 2 minutes it is dropped, never delivered late. Games with constant
  input therefore never get interrupted (on purpose).
- **Notch drop-down**: reuses the pill island. A say is a pill entry `glim-say` that opens itself for 15 s and stays 45 s.
  Buttons: Open chat (counts as "used the help" = yes), 👍, 👎 Not now. The words are also put in the main chat (with the same
  👍/👎 row) so nothing is lost if Ben was away.
- **Notch off** → `Notification` (Electron). It has no 👍/👎 buttons (macOS action buttons need a signed app); the chat copy has them.
- **Ear icon** shows only while always-on is on (any sense on). Priority: 😴 asleep > 😲 (20 s after a big surprise) > 💭 a tick or
  thinking Mote in flight > 📚 learning > 😴 resting.

## Phase 2 (speak-o-meter)
- **Model**: logistic regression, 25 hand-made features (8 app categories, 5 activities, minutes since the last say (log scale),
  3 urges, surprise, stuck-error, stuck-page, urgent). Threshold 0.5. Prior weights: quiet (bias −1.2), stuck error +3,
  same page 10+ min +1.8, typing −4, game −2, video −1.2. Ben's feedback moves it from there.
- **Feedback weights**: "not now/stop/later/shh/quiet/busy" in his next chat 3 (no); 👎 2 (no); ignored 10 min 0.5 (no);
  👍 2 (yes); clicking through ("Open chat") 1.5 (yes); any other reply 1 (yes). Online step lr 0.35 with a small pull back to the
  prior (one 👎 cannot silence it for ever). Nightly refit = 30 passes over the whole log from the prior, lr 0.1.
- **Where it sits**: after the code limits (Ben first, pressure, night, 20-min rate limit). It can only hold a say.
- **Stuck page** = the front app + window title unchanged for 10+ minutes (from the windows sense). **Stuck error** = the same
  error line (numbers and quoted bits ignored) in 3+ observations within 30 minutes.
- **Refit time**: when sleep starts, and once per day at the first minute inside the night window.

## Phase 3 (tiny guesser + Bayesian surprise)
- **Streams**: app category (8), screen category (8: error/code/video/reading/chat/game/quiet/other), sound category
  (speech/music/video/quiet/other). Each is a Dirichlet-count model on (previous category, part of the day: four 6-hour parts).
  A context seen for the first time borrows up to 50 counts from the previous-category model, so 06:00 does not reset its beliefs.
- **The ~1 s tick** re-observes the latest front app from the windows sense, which is still only *sampled* every 20 s (v1 rate;
  the helper is not spawned every second). Staying in the same app counts as "the next app = the same app".
- **Surprise** = KL(Dir(after) ‖ Dir(before)) in nats, closed form (lgamma/digamma in plain JS). Big = ≥ 1 nat, at most one
  filed per stream per minute. Big → `aoLoop.wake()` (an early tick that still passes every gate) + a `surprise` entry
  (words only) in alwayson-state.json + the 😲 face for 20 s. Speak-o-meter feature = 1 − e^(−KL), fading over 2 minutes.
- **Nightly retune** of the guesser = counts × 0.8 (old habits fade so it can follow a new routine).
- **Known flaky test**: `first-reply thinking cap` (agent.test.js) fails about 1 run in 3 on its own; agent.js is untouched by
  this work. The v1 brief listed it as a known failure.

## Phase 4 (urges + bored-mode Motes + memory gauge)
- **Batching: not available.** Ben's server (stock mlx_lm `plain_mlx_lm_big.py` behind the 8090 gateway) serves one request at a
  time, so a "batch" of Motes is sent **back-to-back**, one request after another, with the gate re-checked between them.
  `MotePool` takes an optional `askBatch` for a server that can batch; nothing supplies one today.
- **Bored-mode Motes are light "thinking" requests** (no tools, no web): JSON `{claims, question}`. Claims go to the truth check
  (phase 5), the question to the wonder list. The Learn button's web-studying Motes (v1 helpers) are separate and unchanged.
- **Budget**: 🟢 + away (2+ min idle) + AC = 4; 🟢 otherwise = 2; 🟡 = 1 if away, else 0; 🔴 (pressure critical) or swap grew
  ≥ 256 MB in ~30 s = 0. Also 0 while Ben chats/types/is in a call, during sleep, and in the night window (quiet hours, and
  sleep needs the memory).
- **Stopping**: `agent:send` and every composer keystroke ping call `stopAll()` at once (aborts the request in flight); the 1 s
  clock calls `tick()`, which stops all when the gate says 0. Under 🔴 the Learn button's helper Motes are paused too.
- **Urges**: bored fills 0→1 in a quiet 30 min, drains while Ben chats; starts a batch at ≥ 0.6. Curious = 0.15 × wonder-list
  size (decays over ~6 h). Share +0.4 per thing worth telling, fades over ~2 h; it speaks only if the speak-o-meter and the v1
  limits allow, then resets.
- **Second flaky test**: `memory: the block is a snapshot…` failed once under `--test-concurrency=2`, passed 4/4 alone.
