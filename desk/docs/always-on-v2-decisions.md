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
