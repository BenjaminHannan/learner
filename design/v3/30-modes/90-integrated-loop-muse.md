# 90 — Integrated loop (Muse, 2026-09-22)

One process composes every verified piece behind the `fable_agent_loop`
Protocols, so the real ears/mouth drop in the moment they exist. Built by
`scripts/fable_loop90_agent.py` (`build_agent(cfg)` → `Loop90AgentLoop`, an
`AgentLoop` subclass); marks driven by `scripts/fable_loop90_marks.py`.
Additive only: all other modules imported read-only.

## 1. Slot map (each: current occupant → replacement file)

- **Notebook** → `Loop90Notebook`: `GatedThoughtNotebook` (fix77 rule-2 gate)
  with the `VerifiedNotebook` seal discipline (`verify_full` on clean open,
  sidecar seal advanced on every loop save; repair-then-seal on torn tail).
  This notebook IS the verified piece; no replacement.
- **Reasoner** → `QualifierAwareReasoner77` (`scripts/fable_fix77_core.py`).
  No replacement. On qualifier-free questions it agrees with the qual56/B65
  reasoner exactly (Z2 reproduces the sealed bench73 table cell-for-cell).
- **Ears** → `ChainEars`: stage `bench73` (template ears over triples sourced
  from the loop's own notebook, so corrections are inferred from live state),
  stage `fake` (M1 templates for everyday turns), stage `ears47:<ckpt>`
  auto-appended when a checkpoint exists (today: none; neural teach decode is
  UNVALIDATED upstream so the stage abstains). Every stage score passes the
  certified gate: score < tau-hat → abstain/CLARIFY, never write; tau-hat is
  read at run time from
  `artifacts/fable-abstain76-20260921/ltt_summary.json` (tape 0.088756; template
  hits score 1.0, misses 0.0). Replacement: `scripts/fable_ears47_model.py`
  checkpoint via `'ears47:<ckpt>'` in config chain.
- **Mouth** → `FakeMouth` now. Replacement: `scripts/fable_mouth53_mouth.py`
  `Mouth` (borrowed decoder + faithfulness brake) — same Protocol, no loop
  change.
- **Thinker** → exp-89 `QuarantinedThinking89` (present at run time) behind
  `NotebookThinker`; falls back to m2 `Thinking` by import guard. Web text
  stays quarantined; no further replacement.
- **Sleeper** → `HardGate46Sleeper` (`scripts/fable_wire51_adapters.py`): the
  exp-46 recipe (robust loss ε=0.10, harden ±30, unchanged 4-fold gate) called,
  not re-implemented; deterministic audit live on every SLEEP tick. The wire57
  install path (`scripts/fable_wire57_e2e.py` sparse-village subclass + word
  bridge) is the documented upgrade once learned-word questions queue episodes
  (currently idle; reasoner77 exposes no episode feed).
- **Mailbox** → `Loop90Daemon` (daemon74 dirs, heartbeat, STOP, kill-9-safe),
  extended only to log per-turn records/fact-diffs for the acceptance audit.

## 2. Two deliberate design points

- **Structured teaches bypass the single-word line renderer.** The M1 doorway
  line format (`teach <one-word-name> …`) cannot carry bench names like "Yale
  University". Frame actions from the bench73 stage call `Listening._teach`
  directly (same rights, same statuses, multi-word intact); a smoke test
  asserts parity with the line path on single-word names.
- **All bench values teach entity-valued (`->`).** Bench65 teaches every value
  as an entity; mid-chain hops must stay entity-valued or 2-hop questions
  break with BROKEN_CHAIN. Correction inference (same subject+relation, new
  object → `correct`) reads the loop's notebook, mirroring bench73 exactly.

## 3. Evidence (sealed marks, all PASS)

Z1 60/60 statuses, 0 wrong writes via mailbox. Z2 200/200 Edit-200 items in
their expected cells, 0 WRONG (table identical to sealed bench73 run). Z3
69+56 probe verdicts byte-identical to sealed baselines, 8/8 doctrinal checks
on the real notebook/thinker (incl. live tail-edit detection). Z4 D2 kill-9
restart 200/200, 0 wrong, 0 dupes in seeds 1, 2, 3. Z5 config documents all
six plugs; file-built loop smokes OK with all Protocols satisfied.

## 4. What is still fake, and the two replacement files

Still fake: **ears** (template chain, deterministic 1.0/0.0 scores — no neural
perception, no calibrated uncertainty) and **mouth** (template sentences).
Exactly two files replace them: `scripts/fable_ears47_model.py` (checkpoint,
plugged as `'ears47:<ckpt>'` in the ears chain; its calibrated score feeds the
same tau-hat gate) and `scripts/fable_mouth53_mouth.py` (`Mouth`, into the
mouth slot). Nothing else in the loop changes. Also pending: the sleep episode
feed (wire57 path) and any ears47 checkpoint at all.
