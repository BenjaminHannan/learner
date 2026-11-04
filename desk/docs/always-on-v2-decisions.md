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

## Phase 5 (truth-seeking notes)
- **Where sleep reads notes**: the sleep worker reads userData `memory.json` (SLEEPMLX_USERDATA). `maybe` notes live in a
  separate `truth-notes.json`; only `confirmed` notes and corrections are written to memory (`memory.save`). v1's loop "note"
  now goes through the truth check too (it used to write memory directly).
- **Check**: DuckDuckGo search (the existing `webSearch` tool), sites de-duplicated by registrable domain
  (`en.wikipedia.org` = `wikipedia.org`), each result judged by chat's model (JSON supports/contradicts/unclear + correction),
  with a word-overlap fallback that can only "support" or shrug. 2 sites agree → confirmed; 2 contradict → wrong + correction
  "I thought X; actually Y"; unsettled after 3 tries → `unsure` (never reaches sleep). One check at most every 20 s, only when
  the Mote gate is open; chat/typing aborts it.
- **Not changed**: the Learn button's web-studying helper Motes still save their notes with `memory_save`, which already
  demands an exact quote from a page they actually read (evidence check). They are not re-routed through the 2-site check
  tonight: that would mean changing the agent's memory tool for helpers (a bigger, riskier change). Recorded as a gap.
- **Test environment note**: `desk/build/deskhelper` exists in this worktree (v1's build, git-ignored). desk.test.js's `open_app`
  test runs that real helper, so it fails and sometimes hangs the suite (≈2 in 8 solo runs). A fresh worktree without the
  binary passes 8/8. Not caused by this work; left in place (not mine to delete). Suite runs here use a 240 s kill + retry.

## Phase 6 (Learn quiz score)
- **Writer**: 4 searches per level (topic / facts / explained / what is; harder wording for Lv2+), ≤ 5 results each, one page per
  site, the page fetched with plain `fetch` (public http(s) only; localhost/private ranges refused), tags stripped, ≤ 6000 chars
  to chat's model, ≤ 4 questions per page. A question is kept only if its answer text is on that page. Stops at 20. A level
  needs ≥ 5 questions; 3 failed tries → status `failed` (shown in "View quiz").
- **Locked**: stored in `userData/learn-quiz/<topic>.json`, separate from notes/truth notes. Every bored-Mote prompt goes through
  `safeStudier`, which rebuilds it from the bare topic if it contains any locked question. The Learn helper prompt (`LEARN_MOTE`)
  is built from topic + angle only. A confident quiz miss goes on the wonder list as "weak spot in <topic> (quiz L1q3)" and
  becomes "the weak spots of <topic>" as a Mote topic, never the question.
- **Examiner**: chat's model answers with the topic's confirmed notes + memory notes as context (what Glim has learned), JSON
  answer + confidence, recorded before grading. Grading = text match against the source answer (whole answer for ≤ 24 chars,
  ≥ 75 % content words otherwise; whole numbers exact, decimals ±2 %). No model judges the grade.
- **When**: right after writing (unofficial, marked `*`), every 6 h (unofficial), and the first run after each sleep (official).
  A harder level is written once the newest level scores ≥ 80 % officially. Runs only when the Mote gate is open; chat aborts it.
- **Drift guard**: applies to bored-Mote claims for Learn topics (shares a word with the topic, or 2+ words with the topic's
  confirmed notes); off-topic claims are skipped and counted. The v1 Learn helper Motes are not step-gated (same gap as phase 5).

## Phase 7 (diary on ask + settings + sleep)
- **Diary**: "Glim, what did you do?" and variants (what have you been up to / what did you learn while I was away / show me
  your diary …) add a hidden note with a recap of the last 24 h from the activity log (time per topic, quiz changes, quiz
  written, notes confirmed/wrong, surprises, times it spoke up, drift skips). The chat shows only Ben's words; the model phrases
  the answer from the log. The recap is built in exactly one place and never sent unprompted.
- **Consent**: the first-run card now has "Remember my choice" ticked by default (Ben can untick it). Settings > Senses unchanged.
- **Sleep handoff**: confirmed notes and corrections reach the real sleep through memory.md (the sleep worker's existing input).
  Surprises + confirmed + corrections are also written to `userData/alwayson-sleep.json` when sleep starts and in the night
  window. **Gap**: the Python sleep worker (`sleepmlx/lessons.py`) does not read that file yet. It was not changed tonight:
  sleepmlx has its own gates and tests, and the brief keeps this work to the desk app. A follow-up is one reader function
  next to `read_notes`.
- **Retune at night**: speak-o-meter refit + guesser decay run when sleep starts and once per night window (phases 2–3).
- **Smoke check**: main.js loaded under a stubbed Electron with a temp userData, then the always-on functions were driven
  directly (consent, ear, context, gate, note→maybe, say→voice→feedback, surprise, urges, quiz record/tick, truth tick, share,
  diary, handoff, nightly, stop). No exceptions. The gate was closed by the night window, so no model call was made.

## After phase 7 (review fixes)
- The Learn quiz (writer + examiner) now runs whenever a Learn study is on, even with every always-on sense off (the Learn
  button never needed senses). It still obeys Ben first, sleep, the night window and the memory gauge.
- The memory gauge is re-read every 10 s while always-on or a Learn study is on, so 🔴 pauses the Learn helper Motes even
  when the Mote gate is already shut for another reason (it skipped the reading then).

## Gap fixes (2026-11-04, 00:40–04:30, Ben asleep)

### Item 1: surprises and corrections reach sleep
- **Reader**: `sleepmlx/lessons.py read_alwayson()` reads `userData/alwayson-sleep.json` next to `read_notes()`; `recipe.py extras()`
  turns each surprise into a `surprise` card and each correction into an `aocorrection` card in the same `want` dict that saved
  notes and tracking items use (same Item, same retire-when-gone rule, same `cards.jsonl` rows, same eligibility).
- **Never a `maybe`**: only the `surprises` and `corrections` lists are read; any entry carrying a status other than confirmed/wrong
  is dropped and counted (`ao_dropped_maybe`); secret-looking text and ignore.txt matches are dropped like notes.
- **Confirmed notes are not read from the handoff**: the Desk already saves them to memory.md, which sleep already cards, and
  that is where Ben's "forget" works. A correction that is also in memory.md is skipped too (no double card).
- **Weights**: surprise = 0.25 × (1 + min(KL, 3)) (0.25–1.0, so a big surprise weighs up to 4× a note but at most a night fact's
  minimum); correction = 0.5. Like notes, neither can start a night on its own (`trainable_cards` ignores them).
- **Known limit**: a correction Ben deletes from memory.md but that is still in truth-notes.json would still be carded from the
  handoff. Fix later: have the Desk drop corrections from the handoff when their memory note is forgotten.
- **TODO: surprise-picked sleep vs replay-everything (not run; plan fixed now).** Toy first, never the village model.
  Setup: one simulated day stream of ≥ 400 moments with known "new" events (≈10 %) among steady noise; two sleeps with the SAME
  budget of N = 40 replayed cards: arm A picks the 40 highest-KL moments, arm B samples 40 uniformly from all moments; 3 seeds,
  fresh held-out probes about the new events written before the run. Pass mark: arm A's held-out recall beats arm B's by ≥ 10
  points in 3/3 seeds, with no loss > 2 points on an old-skill probe set. Proven wrong if: arm B ties or wins in ≥ 1 seed, or A
  wins only by losing old skills. One change at a time: selection rule only; budget, model, seeds and probes identical.
