---
name: opencode-usage-limit
description: Every Mac/BensPC job's builder and all GLM calls share Ben's opencode Go plan; its usage limit stalled the whole pipeline 09-27 from ~00:57 UTC
metadata:
  type: project
  modified: 2026-09-27T03:02:49.765Z
---
Found by Ben's Mac Claude, relayed by Ben 2026-09-27 03:01 UTC: opencode.log showed `AI_APICallError: Go usage limit exceeded` from about 00:57 UTC (20:57 EDT), still at 02:55. The five builders launched from 01:21 (170 rv390, disklist, k1h peek 2, probe-benspc-hang, probe-mac-only) sat at their first request; .err.txt held only the banner, reply files empty; processes alive. rungo4.sh waits for exit, and the model fallback (muse-spark -> glm-5.3-flash -> qwen3.8-flash, rungo4.sh:12) only happens after exit, so a hung request never falls back.

**Why:** every queued job, BensPC GPU jobs included, is launched by an `opencode run` builder, and GLM data jobs use the same plan. When the limit is hit, nothing runs anywhere, and GLM jobs running at the time likely produced nothing after the limit.
**How to apply:** when Mac jobs stop finishing, check for the usage limit first (via a no-Ben route: watcher status tail, if the Director adds it). Never ask Ben to pay for more ([[thread-manager-spending]]). Treat GLM counts after a limit hit as suspect until the owner re-checks. Director was asked (03:0x) for a watcher usage-limit hold, a wall-clock timeout on `opencode run`, and a filtered log tail in status/watcher.txt.
