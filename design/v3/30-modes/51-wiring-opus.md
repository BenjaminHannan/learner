# 51 — Wiring the real parts into the glue loop (Opus, 2026-09-21)

Agent 4 of the parallel build. Owns `scripts/fable_wire51_*.py`, artifact
`artifacts/fable-wire51-20260921/`, this doc. Additive only: wraps
`fable_agent_loop`, `fable_listening_english`, `fable_notebook_contract`,
`fable_reasoner50`, `fable_reasoner44`, `fable_hardgate46`,
`fable_thinking_m2` — never edits them.

## The problem

The glue loop (`fable_agent_loop`) ships Protocols (`Ears`, `Mouth`,
`Reasoner`, `Sleeper`, `Thinker`) with fakes (`FakeEars`, `LookupReasoner`,
`StubSleeper`, …). Experiment 51 asks: can one process replace every fake
with the real parts built by agents 1–3 and the existing contract, survive
a 40-turn adversarial script, and be resumable after `kill -9`?

## Real vs placeholder (the diagram)

```
                 ┌────────────── fable_agent_loop ──────────────┐
  Ben ─English──▶│ Ears                                          │
                 │   └─ EnglishEars (fable_wire51_adapters)      │
                 │       wraps fable_listening_english           │
                 │       Qwen bridge @127.0.0.1:18081 = PLACEHOLDER
                 │       (parse only; fake-fallback on bridge down)
                 │                                                │
                 │ Listening ──▶ Notebook (contract, real)        │
                 │                                                │
                 │ Reasoner                                       │
                 │   └─ NotebookReasoner (adapter)                │
                 │       PREFERRED: fable_reasoner50 (agent 3)    │
                 │       FALLBACK: fable_reasoner44 + Exp44 ckpt  │
                 │       + logged neural cross-check (44 only)    │
                 │                                                │
                 │ Sleeper                                        │
                 │   └─ HardGate46Sleeper (adapter)               │
                 │       deterministic audit (formula)            │
                 │       Exp-46 recipe via fable_hardgate46       │
                 │       (only if ≥8 word episodes queued)        │
                 │                                                │
                 │ Thinker                                        │
                 │   └─ NotebookThinker (fable_thinking_m2)       │
                 │       assigned topics only; idle otherwise     │
                 │                                                │
                 │ Mouth                                          │
                 │   └─ TemplateMouth (record → English)          │
                 └────────────────────────────────────────────────┘
  persistence: state.json + notebook/events.jsonl (contract, real)
               + decisions.jsonl (hash-chained, torn-tail repair)
```

**Real:** notebook contract, listening doorway, reasoner50 (or 44 wrap),
hardgate46 recipe, thinking module, mouth templates, hash-chained logs.
**Placeholder:** Qwen bridge for ears (Ben's ruling; swap when agent 1's
encoder lands). Everything else is first-party code/weights.

## Design decisions

- **Reasoner preference:** if `fable_reasoner50` imports and exposes
  `FableReasoner50().answer`, use it wholesale (brief: "if agent 3's module
  appears, prefer it"). Otherwise fall back to `fable_reasoner44` with the
  sealed base checkpoint and a per-question neural cross-check
  (`router_runs/agree/disagree` counters). Word-episode queueing runs on
  both paths so the sleeper always has a source of truth.
- **Sleeper:** fires only when the experience log hits the fixed threshold
  (20 — a number, never a model judgement). Audit is a pure formula over
  log + notebook invariants (no `proposed`/`web-quarantine` answering a
  question, no non-taught fact overwriting a taught one). Exp-46 recipe
  (`robust loss`, harden ±30, unchanged 4-fold gate) runs only when ≥8
  episodes are queued; `fable_hardgate46` is imported read-only (it patches
  `fable_reasoner44.fit_word` in place — exactly the registered recipe).
- **Ears:** `auto` mode uses the English parser via the bridge; on
  `(RuntimeError, OSError, TimeoutError)` it falls back to a deterministic
  fake parser (selftest covers this). Deterministic `pick E\d+` bypass runs
  without a model call. Echo-confirmation of writes is off by default
  (`--echo` enables) because it double-prompted scripted turns.
- **Persistence:** the runner adds `decisions.jsonl` (append-only, SHA-256
  hash chain, `fsync` per event) beside the contract's own `events.jsonl`.
  A torn last line is moved aside on resume and never corrupts the next
  append — verified by selftest.

## The 40-turn script

15 teaching turns (12 statements incl. 1 correction + create-2nd-Mira +
ambiguous teach + pick) → **13 fact rows** (12 active, 1 superseded).
15 questions (6 one-hop, 6 two-hop, 3 unanswerable). 5 hearsay traps and
5 small-talk turns must write nothing. Composition is checked by
`fable_wire51_script40.check_composition()` and asserted in selftest.

Why 13 and not 15 facts: the CREATE and AMBIG turns intentionally write no
fact until the pick resolves ambiguity — that is the correct contract
behaviour, and the mark was set to match it.

## Registered result (summary)

`--replay 3` (sealed marks): every integer on target in all 3 runs —
0 wrong writes, 12/12 answers + 3/3 abstentions, 6/6 two-hop, 5+5 traps
silent, 2 sleeps/run with 0 audit violations, backend
`fable_reasoner50`, ears english 40/40, bridge_failures 0. Full table in
`artifacts/fable-wire51-20260921/RESULTS.md`. Predictions P224–P227 all
TRUE.

## Deviations (documented, not hidden)

1. 13 taught rows (not 15) — ambiguity flow costs turns; composition check
   locks this.
2. Echo-confirmation off by default (`--echo` to enable).
3. `word_lookups=0`: English rejects the maternal-grandmother surface before
   the reasoner; abstention accepted via ears clarify phrase.
4. `router_runs=0` under reasoner50 preference (cross-check is 44-fallback
   only; 44 path still selftested with `prefer50=False`).

## Questions for Ben

None blocking — conservative defaults chosen for all four deviations above.
