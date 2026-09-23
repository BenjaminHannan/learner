# 117 — Redteam110 patches on loop102 (Muse, 2026-09-22)

Exp 110 (red team round 2 of the loop102 agent, 62 fresh cases) found two
genuine bugs plus one display defect the round called out in its brief:
(1) F5: loop102's please-strip (`"forget" + t[m.end(1):]`) drops the space,
so "Please forget Mira city" never parses and the stale value stands;
(2) M5: FakeEars `_APOS` (`['']s\b`) matches lowercase 's only, so shouted
possessives ("WHO IS MIRA'S CITY?", "MIRA'S CITY IS OSLO") never split;
(3) internal relation keys leak into replies with underscores ("Saved:
Roberto Merhi's country_of_citizenship is Spain.", "I don't know T01's
maternal_grandmother."). The other four exp-110 BUGs (R4/N6/S3/S6) are
expectation errors with safe agent behaviour and must stay BUG. This
experiment applies the three small fixes and nothing else.

## Design (additive only, no existing file edited)

New files only, prefix `fable_loop117_`: `scripts/fable_loop117_agent.py`
(the patched loop), `scripts/fable_loop117_marks.py` (loop102 marks with
only the agent class swapped), `scripts/fable_loop117_q2.py` (62 exp-110
cases through the sealed exp-110 harness with only the daemon binary
swapped), `scripts/fable_loop117_q4scan.py` (relation-name underscore
scan), artifact `artifacts/fable-loop117-20260922/`, this doc.

- `Loop117Ears(Loop102Ears)`: overrides `_parse_forget` byte-identical to
  loop102 except the please-strip keeps one space
  (`"forget " + t[m.end(1):]`). Guards (verb shape, "?" screen, that-/
  possessive/raw shapes, Forget-as-a-name, prefix resolution) inherited
  unchanged.
- M5: runtime-only override of the `fable_agent_loop._APOS` module global
  to `[''][sS]\b` at import (this process only). `FakeEars._chain` looks
  the global up at call time, so every instance in the wrapped chain
  splits shouted possessives; `FakeEars._relation` still lowercases to the
  same stored key. Chosen over rebuilding the chain because the chain is
  constructed inside loop90 code we must not edit.
- `Loop117Mouth`: wraps the loop102 mouth; `say()` renders `_` as ` ` in
  the final English sentence. All replies flow through `mouth.say`
  (answers and write/clarify texts alike), so every reply is covered while
  actions, relation keys, and notebook rows are never touched.
- `Loop117AgentLoop` inherits the loop102 forget2 path unchanged;
  `Loop117Daemon` inherits the F5 byte-safe mailbox, building the loop117
  agent instead.

## Verification (sealed PASSMARKS, ledger P117.1–P117.5, all PASS)

Q1: F5/M5 repro copies through real loop117 daemons — both OK. Q2: 62/62
exp-110 cases, 0 OK→BUG, BUG→OK exactly F5+M5, still-BUG exactly
R4/N6/S3/S6. Q3: P2 0 OK→BUG/0 still-BUG (same 16 BUG→OK); P3 L1–L6 all
PASS with identical outcomes; P4 0 refusals; 0 new wrong writes. Q4: 0
relation-name leaks. Q5: ~3 min wall (< 20 min), Mac CPU, offline.

## Known diffs (listed, not hidden)

P2-D8 and five P4 replies render spaces where loop102 showed underscores
(verdicts unchanged — the fix working as intended). P3-L2 changed-list
gains J_statuswords-04 (taught value "MISSING_FACT" displays spaced on the
loop117 arm only) and the H_norm shouted teach now parses to a safe
CONFLICT clarify on both in-process arms. Stored keys/values are
byte-identical in all cases (spot-checked `country_of_citizenship`).

## Limits

Template-shape screens, not comprehension: first-name asks still decline,
packed self-questions still clarify, and the mouth spaces every "_",
including inside literal values. Fixes generalise only to the exact
shapes patched.

## What it means / does not mean

Means: the two genuine round-2 bugs are closed end-to-end with zero
regressions across 62 + 64 + L-marks + 30 cases. Does not mean the agent
understands the newly-covered phrasings: coverage is three narrow,
well-located patches on template parsing and reply rendering.
