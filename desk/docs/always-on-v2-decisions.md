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
