# 138k merge (Opus): 138j + 228 src guard + 220 restart index

**Status:** registered PASS on 2026-09-22. Full results: `artifacts/claude-merge138k-20260922/RESULTS.md`.

## What it is

- **Base:** loop138j, not edited.
- **228:** `install_srcguard228()` runs at import, and `SrcGuardMixin228` comes first in the daemon's class list. It fixes the 1-in-800 flip caused by a reused list address in fix170's `_src_of`.
- **220:** `RestartIndex220Mixin` and `build_agent138k` swap `L138d.IndexedLoopNotebook` for `FixedIndexedLoopNotebook`, but only while the agent is being built. This is the same mechanism `build_agent220` uses. After a reload, every event is indexed exactly once.
- **Class order:** `Loop138kDaemon(SrcGuardMixin228, RestartIndex220Mixin, Loop138jDaemon)`.

## Coverage audit

- The only place a notebook is built is `Loop138dAgentLoop.__init__`, and 138f hands off to it.
- **Reverse lookup (190/190b):** reads the 170 cache, which is rebuilt from `inner._triples`.
- **154f negate, 154g replace, 192:** read `nb.facts`, `nb.active` and `nb.events`, and write through `nb.retract` and `_teach`. Those writes update the index through `_apply`.
- **142 compose:** reads `_sr` and `_sro`.

Nothing is left uncovered.

## Result

- K1–K8 all passed.
- There were 4 moves compared with 138j, all predicted: the ghost reply is gone, and 3 duplicate stored triples are gone.
- Frozen suites, fresh dialogs, soak, p2 and sleep smoke are all identical to 138j.
- Latency did not change: median delta −0.04 ms.
- 3 bench runs were byte-identical.
