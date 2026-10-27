# 228: 138i nondeterminism (Opus)

**Cause.** fable_fix170_compose.py keys `_SRC` by `id(triples list)` without holding the list. After
the list is freed (e.g. `_TRIPLES.clear()` once > 8 notebooks exist), a new list can reuse the
address. That is typically the copy made in `fable_qrewrite132.rewrite_question`. `_src_of()` then
returns an older notebook whose version still matches. The fast `compose_n_hop` verify inside
`_trial_start` reads the wrong index, the rewrite is dropped, and the reply is a non-answer
(glued decline, or a self-router line such as "I have no opinions."). It needs earlier notebooks in the same process, so it only
shows in suite runs, and it depends on allocation history, so it looks random.

**Evidence.** Forced (a freed list registered to a donor notebook, sitting on top of the list free-list):
138i 60/60 rewrite-path items flip, 228 0. Natural: a passive detector on unchanged 138i caught a
stale hit on bench132-4hop-076 in the run where that item was the only move.

**Fix.** scripts/claude_fix228_srcguard.py rebinds `F170._src_of` so it answers only for the live
cached list object (`_TRIPLES[id(inner)][1] is triples`). Everything else falls back to the sealed
originals. Agent scripts/claude_loop228_agent.py = 138i + guard.

**Result.** PASS: 3 loaded bench runs 0 moves; rt136/rt143/sessions152 0 moves; sleep smoke pass.
Details: artifacts/claude-determinism228-20260922/RESULTS.md.

**Follow-ups.** Later agents should adopt the guard. The same id()-keyed pattern exists in `_SL`,
`_NAMES`, `_ONEHOP` and `_SORTED`. Those are safe once `_src_of` is exact, because each also checks the
notebook object and its version. Any new cache keyed by `id()` must hold a reference to the object or
check identity.
