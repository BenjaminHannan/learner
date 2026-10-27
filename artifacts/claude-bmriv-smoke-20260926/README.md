# bm-riv smoke: rival arms on Sleep research's smoke panel (Benchmarks thread, 2026-09-26 14:55 UTC)

Not a registered experiment and not scored by this thread. Sleep research asked for real rival replies on its
30-item smoke panel (artifacts/claude-panel-rsn358b3-smoke-20260926/panel.jsonl, seed 36000, sha256 da7202db…12e7;
not a test panel) so it can check that its scorer (scripts/claude_rsn358b3_panel.py score) reads free-form replies
(tables, "Row 1:", echoed puzzles) before the rsn-358b3 gate and its rival arms are sealed.

Runner: scripts/claude_bmriv_rivals.py (selftest 12/12), the format agreed with Sleep research and Month-end:
system "You are a helpful assistant.", the panel message verbatim as the one user turn, the model's own chat
template, greedy, thinking off, at most 512 new tokens.

| Name | Model | Thinking | New tokens |
|---|---|---|---|
| plain1b | MiniCPM5-1B @87179e5c | off | 512 |
| qwen2b | Qwen3.5-2B @15852e8c | off | 512 |
| lfm12b | LFM2.5-1.2B-Instruct @0f604ada | off | 512 |
| qwen2b_think | Qwen3.5-2B @15852e8c | on (report only) | 4096 |

- **Thinking on:** the reply is the text after the last </think>. If the thinking never closes within 4,096 tokens,
  the reply is "" (no answer) and think_closed is false. The thinking text is never scored.
- **Shards:** the thinking-on arm runs as three processes on one GPU, each taking every third item (--shard K/3).
  `merge` then joins them in panel order and refuses a missing or repeated id. This checks the mechanism the real
  run will need, since a single process runs at about 50 tokens a second.
- **Where it runs:** one small rental, handoff/queue/rent-bmrivsmoke.md (label claude-benchmarks-bmrivsmoke,
  $0.30 cap, 40-minute cap).
- **Output:** the replies land in run/rival_<name>.jsonl on builder-outbox, and Sleep research scores them.
